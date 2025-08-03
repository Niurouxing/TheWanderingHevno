# backend/core/contracts.py

from __future__ import annotations
from typing import Any, Callable, Coroutine, Optional, TypeVar
from abc import ABC, abstractmethod

# --- 1. 核心服务接口与类型别名 (由平台内核提供) ---

# 定义一个泛型，常用于 filter 钩子
T = TypeVar('T')

# 插件注册函数的标准签名
PluginRegisterFunc = Callable[['Container', 'HookManager'], None]

class Container(ABC):
    @abstractmethod
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None: raise NotImplementedError
    @abstractmethod
    def resolve(self, name: str) -> Any: raise NotImplementedError

class HookManager(ABC):
    @abstractmethod
    def add_implementation(self, hook_name: str, implementation: Callable, priority: int = 10, plugin_name: str = "<unknown>"): raise NotImplementedError
    @abstractmethod
    async def trigger(self, hook_name: str, **kwargs: Any) -> None: raise NotImplementedError
    @abstractmethod
    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T: raise NotImplementedError
    @abstractmethod
    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]: raise NotImplementedError

# 后台任务管理器是由 app.py 直接创建的平台级服务，所以其接口也属于核心契约
class BackgroundTaskManager(ABC):
    @abstractmethod
    def start(self) -> None: raise NotImplementedError
    @abstractmethod
    async def stop(self) -> None: raise NotImplementedError
    @abstractmethod
    def submit_task(self, coro_func: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> None: raise NotImplementedError

