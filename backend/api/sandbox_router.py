# backend/api/sandbox_router.py

from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Body, Depends, HTTPException

# 【核心修改】从 contracts 和 state 导入
from backend.core.contracts import Sandbox, StateSnapshot, GraphCollection
from backend.core.state import SnapshotStore, get_sandbox_store, get_snapshot_store
from backend.core.engine import ExecutionEngine, get_engine

router = APIRouter(prefix="/api/sandboxes", tags=["Sandboxes"])

class CreateSandboxRequest(BaseModel):
    name: str
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

@router.post("", response_model=Sandbox)
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    sandbox = Sandbox(name=request_body.name)
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
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
    engine: ExecutionEngine = Depends(get_engine)
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    # 【核心修复】直接使用 snapshot_store 来获取最新的快照
    if not sandbox.head_snapshot_id:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
        
    latest_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
    if not latest_snapshot:
        # 这种情况通常是数据不一致的错误，意味着 head_snapshot_id 指向了一个不存在的快照
        raise HTTPException(
            status_code=500, 
            detail=f"Data inconsistency: head snapshot with ID '{sandbox.head_snapshot_id}' not found."
        )
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    return new_snapshot

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    return snapshots

@router.put("/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")
    
    sandbox.head_snapshot_id = snapshot_id
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}