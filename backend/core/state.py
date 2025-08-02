# backend/core/state.py

from __future__ import annotations
import asyncio
import json
from uuid import UUID
from typing import Dict, Any, List, Optional

from fastapi import Request
from pydantic import ValidationError

# 【核心】所有数据模型和事件契约都从唯一的真实来源 'contracts.py' 导入
from backend.core.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionContext, 
    SharedContext,
    BeforeSnapshotCreateContext
)
from backend.core.models import GraphCollection
from backend.core.hooks import HookManager
from backend.core.utils import DotAccessibleDict

# --- Section 1: 状态存储类 (包含逻辑) ---

class SnapshotStore:
    """
    一个简单的内存快照存储。
    它操作从 contracts.py 导入的 StateSnapshot 模型。
    """
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        """保存一个快照。如果已存在，则覆盖并打印警告。"""
        if snapshot.id in self._store:
            pass
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        """根据ID获取一个快照。"""
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        """查找属于特定沙盒的所有快照，并按创建时间排序。"""
        return sorted(
            [s for s in self._store.values() if s.sandbox_id == sandbox_id],
            key=lambda s: s.created_at
        )

    def clear(self):
        """清空所有存储的快照，主要用于测试。"""
        self._store = {}


# --- Section 2: 核心上下文与快照的工厂/助手函数 ---

def create_main_execution_context(
    snapshot: StateSnapshot, 
    services: Dict[str, Any],
    hook_manager: HookManager, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    """
    为顶层图执行创建初始的 ExecutionContext。
    这是一个工厂函数，将复杂的创建逻辑与模型定义分离。
    """
    shared_context = SharedContext(
        world_state=snapshot.world_state.copy(),
        session_info={
            "start_time": snapshot.created_at,
            "turn_count": 0 # 可以根据需要扩展会话信息
        },
        global_write_lock=asyncio.Lock(),
        services=DotAccessibleDict(services)
    )
    return ExecutionContext(
        shared=shared_context,
        initial_snapshot=snapshot,
        run_vars=run_vars or {},
        hook_manager=hook_manager
    )

def create_sub_execution_context(
    parent_context: ExecutionContext, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    """
    为子图（如 system.call 或 system.map）运行创建新的执行上下文。
    它会继承父上下文的共享资源。
    """
    return ExecutionContext(
        shared=parent_context.shared,
        initial_snapshot=parent_context.initial_snapshot,
        run_vars=run_vars or {},
        hook_manager=parent_context.hook_manager
    )

async def create_next_snapshot(
    context: ExecutionContext,
    final_node_states: Dict[str, Any],
    triggering_input: Dict[str, Any]
) -> StateSnapshot:
    """从当前上下文的状态生成下一个快照。"""
    final_world_state = context.shared.world_state
    
    current_graphs = context.initial_snapshot.graph_collection

    snapshot_data = {
        "sandbox_id": context.initial_snapshot.sandbox_id,
        "graph_collection": current_graphs,
        "world_state": final_world_state,
        "parent_snapshot_id": context.initial_snapshot.id,
        "run_output": final_node_states,
        "triggering_input": triggering_input,
    }

    if '__graph_collection__' in final_world_state:
        graph_json_str = final_world_state.pop('__graph_collection__', None)
        if graph_json_str:
            try:
                evolved_graph_dict = json.loads(graph_json_str) if isinstance(graph_json_str, str) else graph_json_str
                evolved_graphs = GraphCollection.model_validate(evolved_graph_dict)
                current_graphs = evolved_graphs
            except (ValidationError, json.JSONDecodeError):
                pass

    snapshot_data = {
        "sandbox_id": context.initial_snapshot.sandbox_id,
        "graph_collection": context.initial_snapshot.graph_collection,
        "world_state": final_world_state,
        "parent_snapshot_id": context.initial_snapshot.id,
        "run_output": final_node_states,
        "triggering_input": triggering_input,
    }

    filtered_snapshot_data = await context.hook_manager.filter(
        "before_snapshot_create",
        snapshot_data,
        context=BeforeSnapshotCreateContext(
            snapshot_data=snapshot_data,
            execution_context=context
        )
    )
    
    final_snapshot_obj = StateSnapshot.model_validate(filtered_snapshot_data)

    return final_snapshot_obj


# --- Section 3: FastAPI 依赖注入函数 ---

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    """依赖注入函数，用于在 API 端点中获取沙盒存储。"""
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    """依赖注入函数，用于在 API 端点中获取快照存储。"""
    return request.app.state.snapshot_store
