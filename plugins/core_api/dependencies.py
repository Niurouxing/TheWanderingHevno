# plugins/core_api/dependencies.py

from typing import Dict, Any
from uuid import UUID
from fastapi import Request

from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot,
    ExecutionEngineInterface, 
    SnapshotStoreInterface
)
from plugins.core_persistence.contracts import PersistenceServiceInterface
from .contracts import AuditorInterface

# 每个依赖注入函数现在只做一件事：从容器中解析服务。
# 类型提示使用我们新定义的接口。

def get_engine(request: Request) -> ExecutionEngineInterface:
    return request.app.state.container.resolve("execution_engine")

def get_snapshot_store(request: Request) -> SnapshotStoreInterface:
    return request.app.state.container.resolve("snapshot_store")

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    # 对于简单的字典存储，可以直接用 Dict
    return request.app.state.container.resolve("sandbox_store")

def get_auditor(request: Request) -> AuditorInterface:
    return request.app.state.container.resolve("auditor")

def get_persistence_service(request: Request) -> PersistenceServiceInterface:
    """FastAPI 依赖注入函数，用于从容器中获取 PersistenceService。"""
    return request.app.state.container.resolve("persistence_service")