# plugins/core_engine/registry.py

from typing import Dict, Type, Callable
import logging

# --- 核心修改: 导入路径本地化 ---
from .interfaces import RuntimeInterface

logger = logging.getLogger(__name__)

class RuntimeRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    # --- 核心修改: 这是一个常规方法，不再是装饰器工厂 ---
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

