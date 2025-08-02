# plugins/core_api/sandbox_router.py

from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from fastapi import APIRouter, Body, Depends, HTTPException

# 从平台核心契约导入数据模型
from backend.core.contracts import Sandbox, StateSnapshot, GraphCollection

# 从本插件的依赖注入文件中导入 "getters"
from .dependencies import get_sandbox_store, get_snapshot_store, get_engine

# 从 core_engine 插件导入其服务/类
from plugins.core_engine.engine import ExecutionEngine
from plugins.core_engine.state import SnapshotStore

router = APIRouter(prefix="/api/sandboxes", tags=["Sandboxes"])

# --- Request/Response Models ---
class CreateSandboxRequest(BaseModel):
    name: str = Field(..., description="The human-readable name for the sandbox.")
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = Field(default_factory=dict)

# --- API Endpoints ---
@router.post("", response_model=Sandbox, status_code=201)
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    """创建一个新的沙盒并生成其初始（创世）快照。"""
    sandbox = Sandbox(name=request_body.name)
    
    if sandbox.id in sandbox_store:
        raise HTTPException(status_code=409, detail=f"Sandbox with ID {sandbox.id} already exists.")

    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request_body.graph_collection,
        world_state=request_body.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    
    return sandbox

@router.post("/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
    engine: ExecutionEngine = Depends(get_engine)
):
    """在沙盒的最新状态上执行一步计算。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not sandbox.head_snapshot_id:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
        
    latest_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
    if not latest_snapshot:
        raise HTTPException(status_code=500, detail=f"Data inconsistency: head snapshot '{sandbox.head_snapshot_id}' not found.")
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    
    return new_snapshot

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(
    sandbox_id: UUID,
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    """获取一个沙盒的所有历史快照，按时间顺序排列。"""
    # 无需检查沙盒是否存在，如果不存在，find_by_sandbox 将返回空列表
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    return snapshots

@router.put("/{sandbox_id}/revert", status_code=200)
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    """将沙盒的状态回滚到指定的历史快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")
    
    sandbox.head_snapshot_id = snapshot_id
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}