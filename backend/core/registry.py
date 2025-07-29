# backend/core/registry.py
from typing import Dict, Type
from backend.core.runtime import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        # 存储类或实例
        self._registry: Dict[str, Union[Type[RuntimeInterface], RuntimeInterface]] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._registry:
            print(f"Warning: Overwriting runtime registration for '{name}'.")
        # 只存储类，不实例化
        self._registry[name] = runtime_class
        print(f"Runtime class '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        entry = self._registry.get(name)
        if entry is None:
            raise ValueError(f"Runtime '{name}' not found.")

        # 如果存储的是类，则实例化并替换它
        if isinstance(entry, type):
            print(f"Instantiating runtime '{name}' for the first time.")
            instance = entry()
            self._registry[name] = instance
            return instance
        
        # 否则，直接返回已有的实例
        return entry

# 创建一个全局单例
runtime_registry = RuntimeRegistry()