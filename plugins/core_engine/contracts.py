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


# --- 2. 核心运行时上下文模型 ---

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