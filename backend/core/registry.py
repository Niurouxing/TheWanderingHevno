# backend/core/registry.py
from typing import Dict, Type
from backend.core.runtime import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        # 只存储类，不存储实例
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._registry:
            print(f"Warning: Overwriting runtime registration for '{name}'.")
        self._registry[name] = runtime_class
        print(f"Runtime class '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found.")
        
        # 总是返回一个新的实例
        return runtime_class()

# 全局单例保持不变
runtime_registry = RuntimeRegistry()