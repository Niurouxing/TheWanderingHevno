# backend/core/hooks.py
import asyncio
import logging
import inspect 
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Awaitable, TypeVar, Optional

# 从平台核心导入最基础的接口
from backend.core.contracts import HookManager as HookManagerInterface, Container

logger = logging.getLogger(__name__)

# 定义可被过滤的数据类型变量
T = TypeVar('T')

# 定义钩子函数的通用签名
HookCallable = Callable[..., Awaitable[Any]]

@dataclass(order=True)
class HookImplementation:
    """封装一个钩子实现及其元数据。"""
    priority: int
    func: HookCallable = field(compare=False)
    plugin_name: str = field(compare=False, default="<unknown>")

class HookManager(HookManagerInterface):
    """
    一个中心化的、上下文感知的服务，负责发现、注册和调度所有钩子实现。
    它能自动将上下文注入到钩子函数中。
    """
    def __init__(self, container: Container): # <-- 构造函数接收 Container
        self._hooks: Dict[str, List[HookImplementation]] = defaultdict(list)
        # 持有核心上下文
        self._shared_context: Dict[str, Any] = {
            "container": container,
            "hook_manager": self
        }
        logger.info("HookManager initialized and context-aware.")

    def add_shared_context(self, name: str, service: Any) -> None:
        """允许在启动过程中向钩子系统添加更多的共享服务。"""
        if name in self._shared_context:
            logger.warning(f"Overwriting shared context for hooks: '{name}'")
        self._shared_context[name] = service

    def _prepare_hook_args(
        self, 
        func: HookCallable, 
        call_context: Dict[str, Any],
        positional_data: Optional[Any] = None
    ) -> tuple[list, dict]:
        """【新增】智能地准备传递给钩子函数的参数。"""
        sig = inspect.signature(func)
        params = sig.parameters
        
        hook_kwargs = {}
        hook_args = []
        
        # 处理位置参数 (主要用于 filter 钩子)
        if positional_data is not None:
            # 假设 filter 的数据是第一个参数
            hook_args.append(positional_data)
        
        # 处理关键字参数
        for name, param in params.items():
            # 跳过已处理的位置参数
            if param.kind == param.POSITIONAL_ONLY or (param.kind == param.POSITIONAL_OR_KEYWORD and name in [p.name for p in params.values() if p.kind != param.KEYWORD_ONLY][:len(hook_args)]):
                continue
            
            if name in call_context:
                hook_kwargs[name] = call_context[name]

        return hook_args, hook_kwargs

    def add_implementation(
        self,
        hook_name: str,
        implementation: HookCallable,
        priority: int = 10,
        plugin_name: str = "<core>"
    ):
        """向管理器注册一个钩子实现。"""
        if not asyncio.iscoroutinefunction(implementation):
            raise TypeError(f"Hook implementation for '{hook_name}' must be an async function.")

        hook_impl = HookImplementation(priority=priority, func=implementation, plugin_name=plugin_name)
        self._hooks[hook_name].append(hook_impl)
        self._hooks[hook_name].sort() # 保持列表按优先级排序（从小到大）
        logger.debug(f"Registered hook '{hook_name}' from plugin '{plugin_name}' with priority {priority}.")

    async def trigger(self, hook_name: str, **kwargs: Any) -> None:
        """
        触发一个“通知型”钩子。并发执行，忽略返回值。
        现在会自动注入上下文。
        """
        if hook_name not in self._hooks:
            return

        # 合并共享上下文和本次调用的临时上下文
        call_context = {**self._shared_context, **kwargs}
        
        implementations = self._hooks[hook_name]
        tasks = []
        for impl in implementations:
            try:
                # 智能准备参数
                _, prepared_kwargs = self._prepare_hook_args(impl.func, call_context)
                tasks.append(impl.func(**prepared_kwargs))
            except Exception as e:
                logger.error(
                    f"Error preparing args for NOTIFICATION hook '{hook_name}' from plugin '{impl.plugin_name}': {e}",
                    exc_info=e
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                impl = implementations[i]
                logger.error(
                    f"Error in NOTIFICATION hook '{hook_name}' from plugin '{impl.plugin_name}': {result}",
                    exc_info=result
                )

    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T:
        """
        触发一个“过滤型”钩子，形成处理链。
        现在会自动注入上下文。
        """
        if hook_name not in self._hooks:
            return data

        call_context = {**self._shared_context, **kwargs}
        current_data = data
        
        for impl in self._hooks[hook_name]:
            try:
                # 智能准备参数
                prepared_args, prepared_kwargs = self._prepare_hook_args(impl.func, call_context, positional_data=current_data)
                current_data = await impl.func(*prepared_args, **prepared_kwargs)
            except Exception as e:
                logger.error(
                    f"Error in FILTER hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        
        return current_data

    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]:
        """
        触发一个“决策型”钩子。按优先级从高到低执行，并返回第一个非 None 的结果。
        现在会自动注入上下文。
        """
        if hook_name not in self._hooks:
            return None

        call_context = {**self._shared_context, **kwargs}

        for impl in reversed(self._hooks[hook_name]):
            try:
                _, prepared_kwargs = self._prepare_hook_args(impl.func, call_context)
                result = await impl.func(**prepared_kwargs)
                if result is not None:
                    logger.debug(
                        f"DECIDE hook '{hook_name}' was resolved by plugin "
                        f"'{impl.plugin_name}' with priority {impl.priority}."
                    )
                    return result
            except Exception as e:
                logger.error(
                    f"Error in DECIDE hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        return None