# plugins/core_engine/contracts.py 

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Callable, Type
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator
from abc import ABC, abstractmethod
from typing_extensions import Literal

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
    @classmethod
    @abstractmethod
    def get_config_model(cls) -> Type[BaseModel]:
        """
        返回一个 Pydantic 模型，该模型定义了此运行时 'config' 字段的结构。
        这将用于自动生成前端编辑器 UI 和进行配置验证。
        """
        # 为没有配置的运行时提供一个安全的默认实现
        class EmptyConfig(BaseModel):
            pass
        return EmptyConfig

    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        node: Optional[GenericNode] = None
    ) -> Dict[str, Any]:
        pass

    @classmethod
    def get_dependency_config(cls) -> Dict[str, Any]:
        """允许运行时声明其依赖解析行为。"""
        return {}



MutationType = Literal["UPSERT", "DELETE", "LIST_APPEND"]
MutationMode = Literal["DIRECT", "SNAPSHOT"]

class Mutation(BaseModel):
    """定义一个独立的、原子性的修改操作。"""
    type: MutationType
    path: str = Field(..., description="从沙盒根开始的完整资源路径，例如 'lore/graphs/main'。")
    value: Any = Field(None, description="对于 UPSERT 和 LIST_APPEND 操作是必需的。")
    mutation_mode: MutationMode = Field(
        default="DIRECT",
        description="仅当路径以'moment/'开头时有效。'DIRECT'直接修改，'SNAPSHOT'创建新历史。"
    )

class MutateResourceRequest(BaseModel):
    mutations: List[Mutation]

class MutateResourceResponse(BaseModel):
    sandbox_id: UUID
    head_snapshot_id: Optional[UUID]

class ResourceQueryRequest(BaseModel):
    paths: List[str]

class ResourceQueryResponse(BaseModel):
    results: Dict[str, Any]

class EditorUtilsServiceInterface(ABC):
    """
    定义了用于安全地、原子性地执行数据修改的核心工具接口。
    """
    @abstractmethod
    async def execute_mutations(self, sandbox: Sandbox, mutations: List[Mutation]) -> Sandbox:
        """
        原子性地执行一批修改操作，并根据操作类型智能地选择
        直接修改沙盒、直接修改快照或创建新快照。
        """
        raise NotImplementedError
    
    @abstractmethod
    async def execute_queries(self, sandbox: Sandbox, paths: List[str]) -> Dict[str, Any]:
        """
        根据提供的路径列表，批量从沙盒中获取数据。
        """
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
    async def delete(self, snapshot_id: UUID) -> None:
        """异步删除一个指定的快照。"""
        raise NotImplementedError

    @abstractmethod
    async def delete_all_for_sandbox(self, sandbox_id: UUID) -> None:
        """异步删除属于特定沙盒的所有快照。"""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """清除存储（在持久化存储中可能为空操作）。"""
        raise NotImplementedError

class SandboxStoreInterface(ABC):
    """定义沙盒存储的核心接口。"""
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化存储，例如从磁盘预加载。"""
        raise NotImplementedError

    @abstractmethod
    async def save(self, sandbox: 'Sandbox') -> None:
        """异步保存一个沙盒。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, key: UUID) -> Optional['Sandbox']:
        """同步从缓存中获取一个沙盒。"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: UUID) -> None:
        """异步删除一个沙盒及其所有相关数据。"""
        raise NotImplementedError

    @abstractmethod
    def values(self) -> List['Sandbox']:
        """同步获取所有缓存的沙盒。"""
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, key: UUID) -> bool:
        """检查一个沙盒是否存在于缓存中。"""
        raise NotImplementedError

    def __getitem__(self, key: UUID) -> 'Sandbox':
        """允许通过字典语法访问。"""
        sandbox = self.get(key)
        if sandbox is None:
            raise KeyError(key)
        return sandbox

# --- 5. API 契约 ---

class StepDiagnostics(BaseModel):
    """用于承载本次执行的诊断信息。"""
    execution_time_ms: float
    detailed_log: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="一个包含本次 step 执行期间所有详细诊断事件的列表。"
    )

class StepResponse(BaseModel):
    """/step 端点的标准响应信封。"""
    status: Literal["COMPLETED", "ERROR"]
    sandbox: Sandbox
    diagnostics: Optional[StepDiagnostics] = None
    error_message: Optional[str] = None