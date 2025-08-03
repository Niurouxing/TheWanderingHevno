# plugins/core_engine/utils.py

from backend.core.contracts import Container



class ServiceResolverProxy:
    """
    一个代理类，它包装一个 DI 容器，使其表现得像一个字典。
    这使得宏系统可以通过 `services.service_name` 语法懒加载并访问容器中的服务。
    """
    def __init__(self, container: Container):
        """
        :param container: 要代理的 DI 容器实例。
        """
        self._container = container
        # 创建一个简单的缓存，避免对同一个单例服务重复调用 resolve
        self._cache: dict = {}

    def __getitem__(self, name: str):
        """
        这是核心魔法所在。当代码执行 `proxy['service_name']` 时，此方法被调用。
        """
        if name in self._cache:
            return self._cache[name]
        
        service_instance = self._container.resolve(name)
        
        self._cache[name] = service_instance
        
        return service_instance

    def get(self, key: str, default=None):
        try:
            return self.__getitem__(key)
        except (ValueError, KeyError):
            return default

    def keys(self):
        return self._container._factories.keys()
    
    def __contains__(self, key: str) -> bool:
        return key in self._container._factories