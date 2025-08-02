# backend/container.py

import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class Container:
    """一个简单的、通用的依赖注入容器。"""
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, bool] = {}
        self._instances: Dict[str, Any] = {}
        # 注意：此处日志可能还未完全配置，但可以安全调用
        # logger.info("DI Container initialized.")

    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """
        注册一个服务工厂。

        :param name: 服务的唯一名称。
        :param factory: 一个创建服务实例的函数 (可以无参，或接收 container 实例)。
        :param singleton: 如果为 True，服务只会被创建一次（单例）。
        """
        if name in self._factories:
            logger.warning(f"Overwriting service registration for '{name}'")
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
        
        try:
            # 尝试将容器本身作为依赖注入到工厂中
            instance = factory(self)
        except TypeError:
            # 如果工厂不接受参数，则直接调用
            instance = factory()

        logger.debug(f"Resolved service '{name}'. Singleton: {self._singletons.get(name, True)}")

        if self._singletons.get(name, True):
            self._instances[name] = instance
        
        return instance