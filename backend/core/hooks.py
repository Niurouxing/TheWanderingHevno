# backend/core/hooks.py

import asyncio
import logging
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable, TypeVar

# 设置一个专用于钩子系统的日志记录器
logger = logging.getLogger("hevno.hooks")

# --- 1. 核心定义与契约 ---

class HookType(str, Enum):
    """定义钩子的三种行为类型。"""
    NOTIFICATION = "notification"  # 并发执行，忽略返回值
    FILTER = "filter"              # 链式执行，修改数据
    DECISION = "decision"            # 顺序执行，首个非None返回值胜出

# 定义可被过滤的数据类型变量，用于类型提示
T = TypeVar('T')

# 定义钩子函数的通用签名
HookCallable = Callable[..., Awaitable[Any]]

@dataclass(order=True)
class HookImplementation:
    """
    一个封装了钩子实现及其元数据的数据结构。
    `order=True` 使得我们可以直接基于 `priority` 对实例列表进行排序。
    """
    priority: int
    # 使用 field(compare=False) 确保函数对象本身不参与排序比较
    func: HookCallable = field(compare=False)
    plugin_name: str = field(compare=False, default="<unknown>")

# --- 2. 核心钩子管理器 ---

class HookManager:
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
        """
        向管理器注册一个钩子实现。

        每次添加后，都会对该钩子的实现列表重新排序，以保证优先级。
        """
        if not asyncio.iscoroutinefunction(implementation):
            raise TypeError(f"Hook implementation for '{hook_name}' must be an async function.")

        hook_impl = HookImplementation(
            priority=priority, 
            func=implementation,
            plugin_name=plugin_name
        )
        self._hooks[hook_name].append(hook_impl)
        # 保持列表按优先级排序（从小到大）
        self._hooks[hook_name].sort() 
        logger.debug(
            f"Registered hook '{hook_name}' from plugin '{plugin_name}' with priority {priority}."
        )

    async def trigger(self, hook_name: str, **kwargs: Any) -> None:
        """
        触发一个“通知型”钩子。
        
        所有注册的实现都会被并发调用。它们的返回值被忽略。
        单个实现的失败不会影响其他实现。
        """
        if hook_name not in self._hooks:
            return

        implementations = self._hooks[hook_name]
        tasks = [
            asyncio.create_task(impl.func(**kwargs)) for impl in implementations
        ]

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
        """
        if hook_name not in self._hooks:
            return data

        current_data = data
        for impl in self._hooks[hook_name]:
            try:
                current_data = await impl.func(current_data, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in FILTER hook '{hook_name}' from plugin '{impl.plugin_name}'. Skipping. Error: {e}",
                    exc_info=e
                )
        
        return current_data

    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]:
        """
        触发一个“决策型”钩子。

        实现将按优先级顺序串行执行，直到有一个返回了非 `None` 的值。
        该返回值将立即成为最终结果，执行链停止。
        如果所有实现都返回 `None` 或失败，则最终结果为 `None`。
        """
        if hook_name not in self._hooks:
            return None

        for impl in self._hooks[hook_name]:
            try:
                result = await impl.func(**kwargs)
                if result is not None:
                    logger.debug(f"Decision made by plugin '{impl.plugin_name}' for hook '{hook_name}'.")
                    return result
            except Exception as e:
                logger.error(
                    f"Error in DECISION hook '{hook_name}' from plugin '{impl.plugin_name}'. Treating as None. Error: {e}",
                    exc_info=e
                )
        
        return None # 如果所有实现都返回 None
