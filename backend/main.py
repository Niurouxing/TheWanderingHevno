# backend/main.py
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.state_models import Sandbox, SnapshotStore, StateSnapshot
from backend.core.loader import load_modules
from backend.core.registry import runtime_registry
from backend.core.services import service_registry, ServiceInterface

from backend.llm.manager import KeyPoolManager, CredentialManager
from backend.llm.registry import provider_registry

# --- 定义可插拔模块 (不变) ---
PLUGGABLE_MODULES = [
    "backend.runtimes",
    "backend.llm.providers",
    "backend.services"
]

class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

# --- 【核心修改 1】 ---
# 将 setup_application 拆分

def create_app() -> FastAPI:
    """只创建 FastAPI 应用实例，不做任何配置。"""
    return FastAPI(
        title="Hevno Backend Engine",
        description="A dynamically loaded, modular execution engine for Hevno.",
        version="0.4.1-modular-hotfix"
    )

def configure_app(app: FastAPI):
    """配置 FastAPI 应用，加载模块并设置状态。"""
    print("--- Configuring FastAPI Application ---")
    
    # 1. 动态加载所有可插拔模块
    load_modules(PLUGGABLE_MODULES)

    # 2. 准备服务实例化所需的依赖
    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    
    provider_registry.instantiate_all()
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    # 3. 实例化服务
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

    # 4. 实例化引擎，注入依赖
    app.state.engine = ExecutionEngine(
        registry=runtime_registry,
        services=services
    )

    # 5. 配置中间件
    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("--- FastAPI Application Configured ---")

# --- 【核心修改 2】 ---
# 创建一个未配置的 app 实例，供 uvicorn 和测试导入
app = create_app()

# 全局存储保持不变
sandbox_store: Dict[UUID, Sandbox] = {}
snapshot_store = SnapshotStore()

# --- API 端点 ---

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


# 修改端点以从 app.state 获取引擎实例
@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(sandbox_id: UUID, user_input: Dict[str, Any] = Body(...)):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    latest_snapshot = sandbox.get_latest_snapshot(snapshot_store)
    if not latest_snapshot:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
    
    # 从 app.state 获取引擎实例来执行 step
    engine: ExecutionEngine = app.state.engine
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
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


if __name__ == "__main__":
    import uvicorn
    # 在直接运行时，配置 app
    configure_app(app)
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)