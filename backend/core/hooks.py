# backend/core/hooks.py
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Awaitable, TypeVar, Optional
from backend.core.contracts import HookManager as HookManagerInterface

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
    一个中心化的服务，负责发现、注册和调度所有钩子实现。
    它的设计是完全通用的，不与任何特定的钩子绑定。
    """
    def __init__(self):
        self._hooks: Dict[str, List[HookImplementation]] = defaultdict(list)
        logger.info("HookManager initialized.")

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
        """触发一个“通知型”钩子。并发执行，忽略返回值。"""
        if hook_name not in self._hooks:
            return

        implementations = self._hooks[hook_name]
        tasks = [impl.func(**kwargs) for impl in implementations]
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
        非常适合用于收集数据。
        """
        if hook_name not in self._hooks:
            return data

        current_data = data
        # 按优先级顺序执行
        for impl in self._hooks[hook_name]:
            try:
                # 每个钩子实现都会接收上一个实现返回的数据
                current_data = await impl.func(current_data, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in FILTER hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        
        return current_data

    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]:
        """
        触发一个“决策型”钩子。按优先级从高到低执行，并返回第一个非 None 的结果。
        """
        if hook_name not in self._hooks:
            return None

        # self._hooks is sorted low-to-high priority, so iterate in reverse.
        for impl in reversed(self._hooks[hook_name]):
            try:
                result = await impl.func(**kwargs)
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