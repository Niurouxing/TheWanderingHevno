# plugins/core_persistence/dependencies.py (新文件)

from fastapi import Request
from .service import PersistenceService

def get_persistence_service(request: Request) -> PersistenceService:
    """FastAPI 依赖注入函数，用于从容器中获取 PersistenceService。"""
    return request.app.state.container.resolve("persistence_service")