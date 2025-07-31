# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Dict, Any, List, Optional


# 1. 导入新的模型
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, LLMRuntime, SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime 
from backend.core.state_models import Sandbox, SnapshotStore, StateSnapshot
from uuid import UUID
from typing import Dict, Any, List

class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None


def setup_application():
    app = FastAPI(
        title="Hevno Backend Engine",
        description="The core execution engine for Hevno project, supporting implicit dependency graphs.",
        version="0.2.0-implicit"
    )
    
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("llm.default", LLMRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
    runtime_registry.register("system.execute", ExecuteRuntime)
    # --- 新运行时注册的地方 ---
    # runtime_registry.register("system.map", MapRuntime)
    # runtime_registry.register("system.call", CallRuntime)
    
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
# 全局单例存储 (在生产中应替换为 Redis/DB)
sandbox_store: Dict[UUID, Sandbox] = {}
snapshot_store = SnapshotStore()
execution_engine = ExecutionEngine(registry=runtime_registry)



@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(
    request: CreateSandboxRequest,
    name: str  # name 作为查询参数
):
    """
    创建一个新的沙盒，并生成其创世快照。
    此版本移除了对 FastAPI 内部 Request 对象的依赖，以实现更纯净的代码。
    """
    # 1. 移除 try...except ValidationError 块。
    #    FastAPI 会在调用此函数之前自动验证 CreateSandboxRequest。
    #    如果验证失败，它会自动返回一个详细的 422 响应。
    sandbox = Sandbox(name=name)
    
    # StateSnapshot 的创建现在不太可能失败，因为 GraphCollection 已被验证。
    # 如果仍有业务逻辑可能失败，可以保留一个更具体的异常捕获。
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
async def execute_sandbox_step(sandbox_id: UUID, user_input: Dict[str, Any]):
    """在沙盒中执行一个步骤，并返回新的状态快照。"""
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
    """获取一个沙盒的所有历史快照。"""
    return snapshot_store.find_by_sandbox(sandbox_id)

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(sandbox_id: UUID, snapshot_id: UUID):
    """将沙盒回滚到指定的历史快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    sandbox.head_snapshot_id = snapshot_id
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on implicit-dependency architecture!"}
