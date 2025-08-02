# plugins/core_api/dependencies.py

from typing import Dict
from uuid import UUID
from fastapi import Request

# 导入其他插件提供的服务或类
from plugins.core_engine.engine import ExecutionEngine
from plugins.core_engine.state import SnapshotStore

# 导入平台核心的契约
from backend.core.contracts import Sandbox

# 注意：我们不直接导入 `Auditor`，因为 `get_auditor` 可以通过容器解析
# from .auditor import Auditor

def get_engine(request: Request) -> ExecutionEngine:
    return request.app.state.container.resolve("execution_engine")

def get_snapshot_store(request: Request) -> SnapshotStore:
    return request.app.state.container.resolve("snapshot_store")

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    return request.app.state.container.resolve("sandbox_store")

def get_auditor(request: Request): # -> Auditor
    return request.app.state.container.resolve("auditor")