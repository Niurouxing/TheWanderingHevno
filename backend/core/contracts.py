# backend/core/contracts.py

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar # 增加 Coroutine
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator
from abc import ABC, abstractmethod

# --- 1. 核心服务接口与类型别名 (用于类型提示) ---

# 定义一个泛型，常用于 filter 钩子
T = TypeVar('T')

# 插件注册函数的标准签名
PluginRegisterFunc = Callable[['Container', 'HookManager'], None]

# 为核心服务定义接口，插件不应直接导入实现，而应依赖这些接口
class Container(ABC):
    @abstractmethod
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None: raise NotImplementedError
    @abstractmethod
    def resolve(self, name: str) -> Any: raise NotImplementedError

class HookManager(ABC):
    @abstractmethod
    def add_implementation(self, hook_name: str, implementation: Callable, priority: int = 10, plugin_name: str = "<unknown>"): raise NotImplementedError
    @abstractmethod
    async def trigger(self, hook_name: str, **kwargs: Any) -> None: raise NotImplementedError
    @abstractmethod
    async def filter(self, hook_name: str, data: T, **kwargs: Any) -> T: raise NotImplementedError
    @abstractmethod
    async def decide(self, hook_name: str, **kwargs: Any) -> Optional[Any]: raise NotImplementedError
# --- 2. 核心持久化状态模型 (从旧 core/models.py 和 core/contracts.py 合并) ---

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


# --- 3. 核心运行时上下文模型 (从旧 core/contracts.py 迁移) ---

class SharedContext(BaseModel):
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: Any # 通常是一个 DotAccessibleDict 包装的容器
    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot
    hook_manager: HookManager
    model_config = {"arbitrary_types_allowed": True}


# --- 4. 系统事件契约 (用于钩子, 从旧 core/contracts.py 迁移) ---

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


# --- 5. 核心服务接口契约 ---
# 这些是插件应该依赖的抽象接口，而不是具体实现类。

class ExecutionEngineInterface(ABC):
    @abstractmethod
    async def step(self, initial_snapshot: 'StateSnapshot', triggering_input: Dict[str, Any] = None) -> 'StateSnapshot':
        raise NotImplementedError

class SnapshotStoreInterface(ABC):
    @abstractmethod
    def save(self, snapshot: 'StateSnapshot') -> None: raise NotImplementedError
    @abstractmethod
    def get(self, snapshot_id: UUID) -> Optional['StateSnapshot']: raise NotImplementedError
    @abstractmethod
    def find_by_sandbox(self, sandbox_id: UUID) -> List['StateSnapshot']: raise NotImplementedError
    # Adding a clear method for testing purposes
    @abstractmethod
    def clear(self) -> None: raise NotImplementedError

class AuditorInterface(ABC):
    @abstractmethod
    async def generate_full_report(self) -> Dict[str, Any]: raise NotImplementedError
    @abstractmethod
    def set_reporters(self, reporters: List['Reportable']) -> None: raise NotImplementedError

class Reportable(ABC): # 如果还没定义成抽象类，现在定义
    @property
    @abstractmethod
    def report_key(self) -> str: pass
    
    @property
    def is_static(self) -> bool: return True
    
    @abstractmethod
    async def generate_report(self) -> Any: pass

class BackgroundTaskManager(ABC):
    @abstractmethod
    def start(self) -> None: raise NotImplementedError
    @abstractmethod
    async def stop(self) -> None: raise NotImplementedError
    @abstractmethod
    def submit_task(self, coro_func: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> None: raise NotImplementedError