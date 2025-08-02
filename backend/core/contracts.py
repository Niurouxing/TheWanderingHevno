# backend/core/contracts.py

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

# 从其他底层模块导入
from backend.core.models import GraphCollection, GraphDefinition, GenericNode, RuntimeInstruction
from backend.core.utils import DotAccessibleDict

# --- Section 1: 核心持久化状态模型 ---

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

# --- Section 2: 核心运行时上下文模型 ---

class SharedContext(BaseModel):
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: DotAccessibleDict
    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot
    hook_manager: Any
    model_config = {"arbitrary_types_allowed": True}

# --- Section 3: 系统事件契约 (原 plugin_types.py) ---
# 这些模型定义了通过 HookManager 分发的事件的数据结构。
# 它们现在是系统的一等公民，而非仅为插件服务。

class NodeContext(BaseModel):
    """包含与单个节点执行相关的上下文。"""
    node: GenericNode
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

class GraphContext(BaseModel):
    """包含与单个图执行相关的上下文。"""
    graph_def: GraphDefinition
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

# 钩子: engine_step_start
class EngineStepStartContext(BaseModel):
    initial_snapshot: StateSnapshot
    triggering_input: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)

# 钩子: engine_step_end
class EngineStepEndContext(BaseModel):
    final_snapshot: StateSnapshot
    model_config = ConfigDict(arbitrary_types_allowed=True)

# 钩子: graph_run_start / graph_run_end
class GraphRunStartContext(GraphContext): pass
class GraphRunEndContext(GraphContext):
    results: Dict[str, Any]

# 钩子: node_execution_*
class NodeExecutionStartContext(NodeContext): pass
class NodeExecutionSuccessContext(NodeContext):
    result: Dict[str, Any]
class NodeExecutionErrorContext(NodeContext):
    exception: Exception

# 钩子: before_config_evaluation / after_macro_evaluation
class BeforeConfigEvaluationContext(NodeContext):
    instruction_config: Dict[str, Any]
class AfterMacroEvaluationContext(NodeContext):
    evaluated_config: Dict[str, Any]

# 钩子: before_snapshot_create
class BeforeSnapshotCreateContext(BaseModel):
    snapshot_data: Dict[str, Any]
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

# 钩子: resolve_node_dependencies
class ResolveNodeDependenciesContext(BaseModel):
    node: GenericNode
    auto_inferred_deps: Set[str]

# 钩子: select_runtime_implementation
class SelectRuntimeImplementationContext(BaseModel):
    instruction: RuntimeInstruction
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)