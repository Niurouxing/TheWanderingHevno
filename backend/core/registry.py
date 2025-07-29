# backend/core/registry.py
from typing import Dict, Type
from backend.core.runtime import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        self._runtimes: Dict[str, RuntimeInterface] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._runtimes:
            print(f"Warning: Overwriting runtime '{name}'.")
        # 我们在这里实例化运行时
        self._runtimes[name] = runtime_class()
        print(f"Runtime '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime = self._runtimes.get(name)
        if runtime is None:
            raise ValueError(f"Runtime '{name}' not found.")
        return runtime

# 创建一个全局单例
runtime_registry = RuntimeRegistry()