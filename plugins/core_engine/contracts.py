# plugins/core_engine/contracts.py 

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Callable
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator
from abc import ABC, abstractmethod

# 从平台核心导入最基础的接口
from backend.core.contracts import HookManager

# --- 1. 核心持久化状态模型 ---

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
    moment: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_snapshot_id: Optional[UUID] = None
    triggering_input: Dict[str, Any] = Field(default_factory=dict)
    run_output: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        frozen=True,
        arbitrary_types_allowed=True 
    )

class Sandbox(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    definition: Dict[str, Any] = Field(...)
    lore: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    icon_updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

# --- 2. 核心运行时上下文模型 (确保有 arbitrary_types_allowed=True) ---
class SharedContext(BaseModel):
    definition_state: Dict[str, Any] = Field(default_factory=dict)
    lore_state: Dict[str, Any] = Field(default_factory=dict)
    moment_state: Dict[str, Any] = Field(default_factory=dict)
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


# --- 3. 系统事件契约 (用于钩子) ---
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


# --- 4. 核心服务接口契约 (关键修改部分) ---

class SubGraphRunner(ABC):
    """定义执行子图能力的抽象接口。"""
    @abstractmethod
    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

class RuntimeInterface(ABC):
    """定义所有运行时必须实现的接口。"""
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        pipeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

    @classmethod
    def get_dependency_config(cls) -> Dict[str, Any]:
        """允许运行时声明其依赖解析行为。"""
        return {}

class EditorUtilsServiceInterface(ABC):
    """
    定义了用于安全地执行“创作式”修改的核心工具的接口。
    """
    @abstractmethod
    async def perform_sandbox_update(self, sandbox: Sandbox, update_function: Callable[[Sandbox], None]) -> Sandbox:
        """异步地直接在 Sandbox 对象上执行一个修改函数 (用于 lore/definition) 并持久化。"""
        raise NotImplementedError

    @abstractmethod
    async def perform_live_moment_update(
        self,
        sandbox: Sandbox,
        update_function: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Sandbox:
        """异步地安全修改当前 'moment' 状态，并创建一个新的历史快照并持久化。"""
        raise NotImplementedError

class MacroEvaluationServiceInterface(ABC):
    """为宏求值逻辑定义服务接口。"""
    @abstractmethod
    def build_context(
        self,
        exec_context: ExecutionContext,
        pipe_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def evaluate(
        self,
        data: Any,
        eval_context: Dict[str, Any],
        lock: asyncio.Lock
    ) -> Any:
        raise NotImplementedError

class ExecutionEngineInterface(ABC):
    """定义执行引擎的核心接口。"""
    @abstractmethod
    async def step(self, sandbox: 'Sandbox', triggering_input: Dict[str, Any] = None) -> 'Sandbox':
        """
        在沙盒的最新状态上执行一步计算，并返回更新后的、已持久化的沙盒对象。
        """
        raise NotImplementedError

class SnapshotStoreInterface(ABC):
    """定义快照存储的核心接口。"""
    @abstractmethod
    async def save(self, snapshot: 'StateSnapshot') -> None:
        """异步保存一个快照。"""
        raise NotImplementedError
    
    @abstractmethod
    def get(self, snapshot_id: UUID) -> Optional['StateSnapshot']:
        """同步从缓存获取一个快照。"""
        raise NotImplementedError
    
    @abstractmethod
    async def find_by_sandbox(self, sandbox_id: UUID) -> List['StateSnapshot']:
        """异步查找并加载属于特定沙盒的所有快照。"""
        raise NotImplementedError
    
    @abstractmethod
    def clear(self) -> None:
        """清除存储（在持久化存储中可能为空操作）。"""
        raise NotImplementedError