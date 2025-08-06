# backend/container.py

import logging
from typing import Dict, Any, Callable, Set
# 1. 将 threading.Lock 替换为 threading.RLock
import threading

from backend.core.contracts import Container as ContainerInterface

logger = logging.getLogger(__name__)


class Container(ContainerInterface):
    """一个简单的、通用的、线程安全的依赖注入容器，带循环依赖检测。"""
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._instances: Dict[str, Any] = {}
        # 2. 使用 RLock (Re-entrant Lock) 替代 Lock
        self._lock = threading.RLock()
        
        # 使用 threading.local() 来创建线程本地的解析栈
        # 每个线程都会有自己独立的 `_resolution_stack` 副本
        self._local = threading.local()

    def _get_resolution_stack(self) -> Set[str]:
        """安全地获取或初始化当前线程的解析栈。"""
        if not hasattr(self._local, 'resolution_stack'):
            self._local.resolution_stack = set()
        return self._local.resolution_stack

    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """注册一个服务工厂。"""
        if name in self._factories:
            logger.warning(f"Overwriting service registration for '{name}'")
        self._factories[name] = factory
        self._singletons[name] = singleton

    def resolve(self, name: str) -> Any:
        """
        解析（获取）一个服务实例。
        此方法是线程安全的，并能检测循环依赖。
        """
        # 循环依赖检测
        resolution_stack = self._get_resolution_stack()
        if name in resolution_stack:
            path = " -> ".join(list(resolution_stack) + [name])
            raise RuntimeError(f"Circular dependency detected: {path}")

        resolution_stack.add(name)

        try:
            # --- 原有的双重检查锁定逻辑 ---
            is_singleton = self._singletons.get(name, True)
            if is_singleton and name in self._instances:
                return self._instances[name]

            if name not in self._factories:
                raise ValueError(f"Service '{name}' not found in container.")

            if not is_singleton:
                factory = self._factories[name]
                try:
                    return factory(self)
                except TypeError:
                    return factory()

            with self._lock:
                if name in self._instances:
                    return self._instances[name]

                factory = self._factories[name]
                try:
                    instance = factory(self)
                except TypeError:
                    instance = factory()

                logger.debug(f"Resolved service '{name}'. Singleton: True")
                self._instances[name] = instance
                return instance
        finally:
            resolution_stack.remove(name)