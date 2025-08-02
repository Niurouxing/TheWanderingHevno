# backend/core/contracts.py
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Coroutine, TypeVar
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator

# --- 类型别名 ---
PluginRegisterFunc = Callable[['Container', 'HookManager'], None]
T = TypeVar('T') # 用于泛型

# --- 核心服务接口契约 (用于类型提示) ---
class Container:
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None: raise NotImplementedError
    def resolve(self, name: str) -> Any: raise NotImplementedError

class HookManager:
    async def trigger(self, hook_name: str, **kwargs: Any) -> None: raise NotImplementedError
    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T: raise NotImplementedError
    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]: raise NotImplementedError


# --- 核心持久化状态模型 ---
# (从原 core/contracts.py, core/models.py, persistence/models.py 迁移和合并)

class RuntimeInstruction(BaseModel):
    runtime: str
    config: Dict[str, Any] = Field(default_factory=dict)

class GenericNode(BaseModel):
    id: str
    run: List[RuntimeInstruction]
    depends_on: Optional[List[str]] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphDefinition(BaseModel):
    nodes: List[GenericNode]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v

class StateSnapshot(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    graph_collection: GraphCollection
    world_state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_snapshot_id: Optional[UUID] = None
    triggering_input: Dict[str, Any] = Field(default_factory=dict)
    run_output: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(frozen=True)

class Sandbox(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- 核心运行时上下文模型 ---
# (从原 core/contracts.py 迁移)

class SharedContext(BaseModel):
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: Any
    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot
    hook_manager: HookManager
    model_config = {"arbitrary_types_allowed": True}


# --- 系统事件契约 (用于钩子) ---
# (从原 core/contracts.py 迁移)

class NodeContext(BaseModel):
    node: GenericNode
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepStartContext(BaseModel):
    initial_snapshot: StateSnapshot
    triggering_input: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepEndContext(BaseModel):
    final_snapshot: StateSnapshot
    model_config = ConfigDict(arbitrary_types_allowed=True)

class NodeExecutionStartContext(NodeContext): pass
class NodeExecutionSuccessContext(NodeContext):
    result: Dict[str, Any]
class NodeExecutionErrorContext(NodeContext):
    exception: Exception

class BeforeConfigEvaluationContext(NodeContext):
    instruction_config: Dict[str, Any]
class AfterMacroEvaluationContext(NodeContext):
    evaluated_config: Dict[str, Any]

class BeforeSnapshotCreateContext(BaseModel):
    snapshot_data: Dict[str, Any]
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ResolveNodeDependenciesContext(BaseModel):
    node: GenericNode
    auto_inferred_deps: Set[str]