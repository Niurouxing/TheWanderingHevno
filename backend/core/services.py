# backend/core/services.py
from typing import Dict, Any, Type, Callable


class ServiceInterface:
    """一个可选的基类或标记接口，用于所有服务。"""
    pass

class ServiceRegistry:
    """管理整个应用中的核心服务。"""
    def __init__(self):

        self._service_classes: Dict[str, Type[ServiceInterface]] = {}


    def register(self, name: str) -> Callable[[Type[ServiceInterface]], Type[ServiceInterface]]:
        """装饰器，用于注册服务类。"""
        def decorator(service_class: Type[ServiceInterface]) -> Type[ServiceInterface]:
            if name in self._service_classes:
                print(f"Warning: Overwriting service registration for '{name}'.")
            self._service_classes[name] = service_class
            print(f"Service '{name}' registered via decorator: {service_class.__name__}")
            return service_class
        return decorator

    def get_class(self, name: str) -> Type[ServiceInterface] | None:
        """获取已注册的服务类。"""
        return self._service_classes.get(name)


# 全局单例
service_registry = ServiceRegistry()