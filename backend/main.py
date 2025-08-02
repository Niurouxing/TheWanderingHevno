# backend/main.py
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Body, Depends, Request # <--- 1. 导入 Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.state import Sandbox, SnapshotStore, StateSnapshot
from backend.core.loader import load_modules
from backend.core.registry import runtime_registry
from backend.core.services import service_registry
from backend.llm.manager import KeyPoolManager, CredentialManager
from backend.llm.registry import provider_registry
from backend.core.reporting import auditor_registry, Auditor
from backend.runtimes.reporters import RuntimeReporter
from backend.llm.reporters import LLMProviderReporter
from backend.api.reporters import SandboxStatsReporter

PLUGGABLE_MODULES = [
    "backend.runtimes",
    "backend.llm.providers",
    "backend.services"
]

class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

def create_app() -> FastAPI:
    return FastAPI(
        title="Hevno Backend Engine",
        description="A dynamically loaded, modular execution engine for Hevno.",
        version="0.5.0-di-refactor"
    )

def configure_app(app: FastAPI):
    # --- 1. 初始化核心状态存储 ---
    app.state.sandbox_store = {}
    app.state.snapshot_store = SnapshotStore()
    
    # --- 2. 审阅官系统初始化 ---
    print("--- Configuring Auditor System ---")
    
    # 实例化所有 Reporter
    runtime_reporter = RuntimeReporter()
    llm_reporter = LLMProviderReporter()
    # <--- 2. 修正 Reporter 初始化: 只实例化一次，并使用 app.state ---
    sandbox_stats_reporter = SandboxStatsReporter(
        app.state.sandbox_store, 
        app.state.snapshot_store
    )

    # 向注册表注册
    auditor_registry.register(runtime_reporter)
    auditor_registry.register(llm_reporter)
    auditor_registry.register(sandbox_stats_reporter)

    # 创建 Auditor 服务并存入 app.state
    app.state.auditor = Auditor(auditor_registry)
    print("--- Auditor System Configured ---")

    # --- 3. 应用配置与服务加载 ---
    print("--- Configuring FastAPI Application ---")
    
    load_modules(PLUGGABLE_MODULES)

    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    
    provider_registry.instantiate_all()
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    if is_debug_mode:
        MockLLMServiceClass = service_registry.get_class("mock_llm")
        if not MockLLMServiceClass: raise RuntimeError("MockLLMService not registered!")
        llm_service_instance = MockLLMServiceClass()
    else:
        LLMServiceClass = service_registry.get_class("llm")
        if not LLMServiceClass: raise RuntimeError("LLMService not registered!")
        llm_service_instance = LLMServiceClass(
            key_manager=key_manager,
            provider_registry=provider_registry,
            max_retries=3
        )

    services = {"llm": llm_service_instance}

    app.state.engine = ExecutionEngine(
        registry=runtime_registry,
        services=services
    )

    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("--- FastAPI Application Configured ---")

app = create_app()

# --- 依赖注入函数 ---
def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    return request.app.state.snapshot_store

def get_engine(request: Request) -> ExecutionEngine:
    return request.app.state.engine

# --- API 端点 (全部使用依赖注入) ---

@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    name: str,
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store)
):
    sandbox = Sandbox(name=name)
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request_body.graph_collection,
        world_state=request_body.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    return sandbox

@app.get("/api/system/report", tags=["System"])
async def get_system_report(request: Request):
    auditor: Auditor = request.app.state.auditor
    return await auditor.generate_full_report()

@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict = Depends(get_sandbox_store), # <--- 3. 注入依赖
    snapshot_store: SnapshotStore = Depends(get_snapshot_store), # <--- 3. 注入依赖
    engine: ExecutionEngine = Depends(get_engine) # <--- 3. 注入依赖
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    latest_snapshot = sandbox.get_latest_snapshot(snapshot_store)
    if not latest_snapshot:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    return new_snapshot

@app.get("/api/sandboxes/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store), # <--- 3. 注入依赖
    snapshot_store: SnapshotStore = Depends(get_snapshot_store) # <--- 3. 注入依赖
):
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots and not sandbox_store.get(sandbox_id):
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return snapshots

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store), # <--- 3. 注入依赖
    snapshot_store: SnapshotStore = Depends(get_snapshot_store) # <--- 3. 注入依赖
):
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    
    sandbox.head_snapshot_id = snapshot_id
    # 注意: 对字典的修改是原地生效的，但如果 sandbox_store 是其他类型的对象，
    # 重新赋值（sandbox_store[sandbox.id] = sandbox）会更安全。
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on runtime-centric architecture!"}

if __name__ == "__main__":
    import uvicorn
    configure_app(app)
    uvicorn.run(app, host="0.0.0.0", port=8000)