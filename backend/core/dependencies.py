# backend/core/dependencies.py
from typing import Any
from fastapi import Request

class Service:
    """
    一个可调用的依赖注入类，用于 FastAPI 的 Depends。
    它使得我们可以按名称从容器中解析任何服务。
    """
    def __init__(self, service_name: str):
        """
        初始化时，只记录需要解析的服务名称。
        :param service_name: 在 DI 容器中注册的服务名称。
        """
        self.service_name = service_name

    def __call__(self, request: Request) -> Any:
        """
        当 FastAPI 处理 Depends(Service(...)) 时，它会调用这个方法。
        我们从请求中获取容器，并解析所需的服务。
        """
        try:
            return request.app.state.container.resolve(self.service_name)
        except ValueError as e:
            # 如果服务未找到，这将自动导致一个清晰的服务器错误
            raise ValueError(f"Could not resolve service '{self.service_name}' from container. "
                             f"Ensure the plugin providing this service is installed and registered correctly.") from e