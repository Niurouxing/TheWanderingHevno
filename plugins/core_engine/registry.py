# plugins/core_engine/registry.py
from typing import Dict, Type, Callable
from backend.core.interfaces import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    def register(self, name: str) -> Callable[[Type[RuntimeInterface]], Type[RuntimeInterface]]:
        """
        一个可以作为装饰器使用的注册方法。
        用法:
        @runtime_registry.register("system.input")
        class InputRuntime(RuntimeInterface):
            ...
        """
        def decorator(runtime_class: Type[RuntimeInterface]) -> Type[RuntimeInterface]:
            if name in self._registry:
                print(f"Warning: Overwriting runtime registration for '{name}'.")
            self._registry[name] = runtime_class
            print(f"Runtime '{name}' registered via decorator.")
            return runtime_class
        return decorator

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found.")
        return runtime_class()

# 全局单例
runtime_registry = RuntimeRegistry()