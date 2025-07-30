# backend/main.py
from fastapi import FastAPI, HTTPException, Body, Request 
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Dict, Any, List, Optional
from fastapi.exceptions import RequestValidationError # <--- 2. 导入 RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler # <--- 3. 导入处理器


# 1. 导入新的模型
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime, SetWorldVariableRuntime
from backend.core.sandbox_models import Sandbox, SnapshotStore, StateSnapshot
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
    runtime_registry.register("system.template", TemplateRuntime)
    runtime_registry.register("llm.default", LLMRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
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
    # 'fastapi_request' 是一个临时的变通方法，更优雅的方法见下文
    fastapi_request: Request, # 接收原始的 FastAPI Request 对象
    name: str,
    request: CreateSandboxRequest
):
    """创建一个新的沙盒，并生成其创世快照。"""
    try:
        # Pydantic v2.6+ 引入了 `model_validate` 的严格模式，
        # 我们可以利用它来强制重新验证。
        # 即使 request 对象已经存在，我们再次验证它以确保捕获所有错误。
        # 这一步其实是触发 StateSnapshot 内部验证的关键。
        # 如果 StateSnapshot 构造失败，我们捕获异常。
        
        sandbox = Sandbox(name=name)
        genesis_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            graph_collection=request.graph_collection,
            world_state=request.initial_state or {}
        )
        
        # 为了更明确地触发验证，我们甚至可以这样做：
        # GraphCollection.model_validate(request.graph_collection.root)

    except ValidationError as e:
        # --- 5. 关键修复 ---
        # 我们捕获了在函数体内发生的 ValidationError。
        # 现在，我们不想自己构建 HTTPException，而是想模拟 FastAPI 
        # 在参数绑定阶段本应做的事情。
        # 我们将这个 ValidationError 包装成 RequestValidationError，
        # 然后调用 FastAPI 的标准处理器来生成响应。
        # 这可以保证响应格式与框架自动生成的完全一致，且不会有序列化问题。
        return await request_validation_exception_handler(
            fastapi_request, RequestValidationError(e.errors())
        )

    # 如果代码能执行到这里，说明 StateSnapshot 创建成功
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
