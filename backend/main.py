# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Dict, Any, List, Optional
from uuid import UUID

# 1. 导入新的模型
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, LLMRuntime, SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime
from backend.runtimes.codex.invoke_runtime import InvokeRuntime
from backend.core.state_models import Sandbox, SnapshotStore, StateSnapshot


class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

def setup_application():
    app = FastAPI(
        title="Hevno Backend Engine",
        description="The core execution engine for Hevno project, supporting runtime-centric, sequential node execution.",
        version="0.3.2-map-runtime" # 版本号更新
    )
    
    # 基础运行时
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("llm.default", LLMRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
    
    # 控制流运行时
    runtime_registry.register("system.execute", ExecuteRuntime)
    runtime_registry.register("system.call", CallRuntime)
    runtime_registry.register("system.map", MapRuntime)
    runtime_registry.register("system.invoke", InvokeRuntime)

    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = setup_application()
sandbox_store: Dict[UUID, Sandbox] = {}
snapshot_store = SnapshotStore()
execution_engine = ExecutionEngine(registry=runtime_registry)

@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(request: CreateSandboxRequest, name: str):
    sandbox = Sandbox(name=name)
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request.graph_collection,
        world_state=request.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    return sandbox

@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(sandbox_id: UUID, user_input: Dict[str, Any] = Body(...)):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    latest_snapshot = sandbox.get_latest_snapshot(snapshot_store)
    if not latest_snapshot:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
    new_snapshot = await execution_engine.step(latest_snapshot, user_input)
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    return new_snapshot

@app.get("/api/sandboxes/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(sandbox_id: UUID):
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots and not sandbox_store.get(sandbox_id):
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return snapshots

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(sandbox_id: UUID, snapshot_id: UUID):
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    sandbox.head_snapshot_id = snapshot_id
    sandbox_store[sandbox.id] = sandbox # 确保更新存储中的沙盒对象
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on runtime-centric architecture!"}