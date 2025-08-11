# plugins/core_engine/registry.py

from typing import Dict, Type, Callable
import logging

from .contracts import RuntimeInterface

logger = logging.getLogger(__name__)

class RuntimeRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        """
        向注册表注册一个运行时类。
        """
        if name in self._registry:
            logger.warning(f"Overwriting runtime registration for '{name}'.")
        self._registry[name] = runtime_class
        logger.debug(f"Runtime '{name}' registered to the registry.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        """
        获取一个运行时的【新实例】。
        """
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found in registry.")
        return runtime_class()

    def get_runtime_class(self, name: str) -> Type[RuntimeInterface]:
        """
        获取运行时类本身，而不是一个实例。
        这对于访问类方法 (如 get_dependency_config) 非常有用。
        """
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime class for '{name}' not found in registry.")
        return runtime_class

