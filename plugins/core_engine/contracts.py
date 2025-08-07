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

# --- 1. 核心持久化状态模型 (已重构) ---

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
    """
    【已重构】代表一个特定时间点的“瞬时”状态。
    所有在此模型中的数据，都会在读档时被回滚。
    """
    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    # 【新】moment: 存储所有与快照绑定的、可回滚的状态 (如玩家HP, 任务进度, 记忆系统)。
    moment: Dict[str, Any] = Field(
        default_factory=dict,
        description="与快照绑定的即时状态，读档时必须回滚。"
    )
    # 【已移除】移除了 world_state 和 graph_collection。

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_snapshot_id: Optional[UUID] = None
    triggering_input: Dict[str, Any] = Field(default_factory=dict)
    run_output: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(frozen=True)

class Sandbox(BaseModel):
    """
    【已重构】代表一个完整的、可交互的世界实例。
    它现在包含了静态的“蓝图”和动态演化的“世界历史”。
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    
    # 【新】definition: 沙盒的“设计蓝图”，在运行时只读。
    definition: Dict[str, Any] = Field(
        ...,
        description="沙盒的设计蓝图，约定包含 initial_lore 和 initial_moment。运行时只读。"
    )
    # 【新】lore: 沙盒的“世界法典”，跨快照共享，读档不回滚。
    lore: Dict[str, Any] = Field(
        default_factory=dict,
        description="沙盒的世界法典，跨快照共享，读档不回滚。用于存储图定义、Codex等。"
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    icon_updated_at: Optional[datetime] = None


# --- 2. 核心运行时上下文模型 (已重构) ---

class SharedContext(BaseModel):
    """
    【已重构】图在单次执行期间共享的、隔离的上下文。
    它包含了三层作用域的运行时拷贝。
    """
    # 【新】三层作用域的运行时状态，从持久化模型深拷贝而来。
    definition_state: Dict[str, Any] = Field(default_factory=dict)
    lore_state: Dict[str, Any] = Field(default_factory=dict)
    moment_state: Dict[str, Any] = Field(default_factory=dict)
    
    # 【已移除】移除了 world_state。

    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: Any # 通常是一个 DotAccessibleDict 包装的容器
    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    """【保持不变】执行上下文的顶层结构。"""
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot
    hook_manager: HookManager
    model_config = {"arbitrary_types_allowed": True}


# --- 3. 系统事件契约 (用于钩子) ---
# ... (此部分无需修改) ...
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


# --- 4. 核心服务接口契约 (由 core_engine 实现) ---

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
        """
        一个类方法，允许运行时声明其依赖解析行为。
        解析器将使用这些元数据来指导其扫描过程。

        返回的字典可以包含：
        - 'ignore_fields': 一个字段名列表。解析器将完全跳过对这些字段的值进行依赖推断。
        - 'scan_only_fields': 一个字段名列表。解析器将只扫描这些字段，忽略其他所有字段。

        默认实现返回一个空字典，表示采用标准的全量扫描策略。
        """
        return {}

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
    @abstractmethod
    def clear(self) -> None: raise NotImplementedError