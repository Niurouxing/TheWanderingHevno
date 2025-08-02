# backend/core/plugin_types.py

from typing import Dict, Any, Set, Optional, Type
from pydantic import BaseModel, ConfigDict

# 从现有模块导入核心数据结构，以构建钩子上下文
from backend.core.models import GraphDefinition, GenericNode, RuntimeInstruction
from backend.core.state import StateSnapshot, ExecutionContext
from backend.core.interfaces import RuntimeInterface

# --- 通用上下文模型 ---
# 避免在每个模型中重复定义常用字段

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

# --- 引擎与图执行流钩子 (通知型) ---

class EngineStepStartContext(BaseModel):
    initial_snapshot: StateSnapshot
    triggering_input: Dict[str, Any]
    model_config = ConfigDict(arbitrary_types_allowed=True)

class EngineStepEndContext(BaseModel):
    final_snapshot: StateSnapshot
    model_config = ConfigDict(arbitrary_types_allowed=True)

class GraphRunStartContext(GraphContext):
    pass

class GraphRunEndContext(GraphContext):
    results: Dict[str, Any]

# --- 节点执行周期钩子 (通知型) ---

class NodeExecutionStartContext(NodeContext):
    pass

class NodeExecutionSuccessContext(NodeContext):
    result: Dict[str, Any]

class NodeExecutionErrorContext(NodeContext):
    exception: Exception

# --- 指令配置处理钩子 (过滤型) ---

class BeforeConfigEvaluationContext(NodeContext):
    """
    上下文对象，传递给 `before_config_evaluation` 过滤型钩子。
    插件可以修改 `instruction_config` 字典。
    """
    instruction_config: Dict[str, Any]

class AfterMacroEvaluationContext(NodeContext):
    """
    上下文对象，传递给 `after_macro_evaluation` 过滤型钩子。
    插件可以修改宏求值后的 `evaluated_config` 字典。
    """
    evaluated_config: Dict[str, Any]

# --- 状态持久化钩子 (过滤型) ---

class BeforeSnapshotCreateContext(BaseModel):
    """
    上下文对象，传递给 `before_snapshot_create` 过滤型钩子。
    插件可以修改 `snapshot_data` 字典，以注入自定义元数据。
    """
    snapshot_data: Dict[str, Any]
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)

# --- 核心逻辑覆盖钩子 (决策型) ---

class ResolveNodeDependenciesContext(BaseModel):
    """
    上下文对象，传递给 `resolve_node_dependencies` 决策型钩子。
    插件可以返回一个全新的依赖集合 (Set[str]) 来覆盖默认行为。
    """
    node: GenericNode
    auto_inferred_deps: Set[str]

class SelectRuntimeImplementationContext(BaseModel):
    """
    上下文对象，传递给 `select_runtime_implementation` 决策型钩子。
    插件可以返回一个全新的运行时实例 (RuntimeInterface) 来覆盖默认行为。
    """
    instruction: RuntimeInstruction
    execution_context: ExecutionContext
    model_config = ConfigDict(arbitrary_types_allowed=True)


# 确保 Pydantic 能够正确处理所有向前引用
NodeContext.model_rebuild(force=True)
GraphContext.model_rebuild(force=True)
EngineStepStartContext.model_rebuild(force=True)
EngineStepEndContext.model_rebuild(force=True)
GraphRunStartContext.model_rebuild(force=True)
GraphRunEndContext.model_rebuild(force=True)
NodeExecutionStartContext.model_rebuild(force=True)
NodeExecutionSuccessContext.model_rebuild(force=True)
NodeExecutionErrorContext.model_rebuild(force=True)
BeforeConfigEvaluationContext.model_rebuild(force=True)
AfterMacroEvaluationContext.model_rebuild(force=True)
BeforeSnapshotCreateContext.model_rebuild(force=True)
ResolveNodeDependenciesContext.model_rebuild(force=True)
SelectRuntimeImplementationContext.model_rebuild(force=True)