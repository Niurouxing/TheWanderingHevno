# backend/container.py
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class Container:
    """一个简单的依赖注入容器。"""
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._instances: Dict[str, Any] = {}
        logger.info("DI Container initialized.")

    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """
        注册一个服务工厂。

        :param name: 服务的唯一名称。
        :param factory: 一个创建服务实例的函数 (可以无参，或接收 container 实例)。
        :param singleton: 如果为 True，服务只会被创建一次。
        """
        logger.debug(f"Registering service '{name}'. Singleton: {singleton}")
        self._factories[name] = factory
        self._singletons[name] = singleton

    def resolve(self, name: str) -> Any:
        """
        解析（获取）一个服务实例。

        如果服务是单例且已被创建，则返回现有实例。
        否则，调用其工厂函数创建新实例。
        """
        if name in self._instances and self._singletons.get(name, True):
            return self._instances[name]

        if name not in self._factories:
            raise ValueError(f"Service '{name}' not found in container.")

        factory = self._factories[name]
        
        # 简单的依赖注入：如果工厂需要容器本身，就传递它
        # 这是一个简化处理，更复杂的可以用 inspect.signature
        try:
            instance = factory(self)
        except TypeError:
            instance = factory()

        logger.debug(f"Resolved service '{name}'.")

        if self._singletons.get(name, True):
            self._instances[name] = instance
        
        return instance