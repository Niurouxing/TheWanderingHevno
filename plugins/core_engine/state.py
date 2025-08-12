# plugins/core_engine/state.py 

from __future__ import annotations
import asyncio
import json
from copy import deepcopy
from uuid import UUID
from typing import Dict, Any, List, Optional, Tuple

from fastapi import Request
from pydantic import ValidationError

from backend.core.contracts import HookManager, Container
from .contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionContext, 
    SharedContext,
    BeforeSnapshotCreateContext,
    GraphCollection
)
from backend.core.utils import DotAccessibleDict, unwrap_dot_accessible_dicts
from .utils import ServiceResolverProxy 

# --- Section 1: 状态存储类 ---

class SnapshotStore:
    """
    一个简单的内存快照存储。
    它操作从 contracts.py 导入的 StateSnapshot 模型。
    """
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        if snapshot.id in self._store:
            pass
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        return sorted(
            [s for s in self._store.values() if s.sandbox_id == sandbox_id],
            key=lambda s: s.created_at
        )

    def clear(self):
        self._store.clear()


# --- Section 2: 核心上下文与快照的工厂/助手函数  ---

def create_main_execution_context(
    snapshot: StateSnapshot, 
    sandbox: Sandbox, 
    container: Container,
    hook_manager: HookManager, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
    """
    从持久化的 Snapshot 和 Sandbox 中，为一次安全的、隔离的执行准备运行时上下文。
    使用深拷贝来防止执行过程意外修改原始状态。
    """
    # 在 run_vars 中添加一个 diagnostics_log 列表
    initial_run_vars = {
        "triggering_input": {},
        "diagnostics_log": []
    }
    if run_vars:
        initial_run_vars.update(run_vars)
        
    shared_context = SharedContext(
        definition_state=deepcopy(sandbox.definition),
        lore_state=deepcopy(sandbox.lore),
        moment_state=deepcopy(snapshot.moment),
        
        session_info={
            "start_time": snapshot.created_at,
            "turn_count": 0
        },
        global_write_lock=asyncio.Lock(),
        services=DotAccessibleDict(ServiceResolverProxy(container))
    )
    return ExecutionContext(
        shared=shared_context,
        initial_snapshot=snapshot,
        run_vars=initial_run_vars,
        hook_manager=hook_manager
    )


def create_sub_execution_context(
    parent_context: ExecutionContext, 
    run_vars: Dict[str, Any] = None
) -> ExecutionContext:
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
) -> Tuple[StateSnapshot, Dict[str, Any]]: 
    """
    从执行完毕的上下文中，创建新的 StateSnapshot 并分离出更新后的 Lore。
    """
    final_moment_state = context.shared.moment_state
    final_lore_state = context.shared.lore_state
    
    # 调用从 backend.core.utils 导入的官方函数
    unwrapped_moment = unwrap_dot_accessible_dicts(final_moment_state)
    unwrapped_lore = unwrap_dot_accessible_dicts(final_lore_state)
    unwrapped_node_states = unwrap_dot_accessible_dicts(final_node_states)
    
    snapshot_data = {
        "sandbox_id": context.initial_snapshot.sandbox_id,
        "moment": unwrapped_moment, 
        "parent_snapshot_id": context.initial_snapshot.id,
        "run_output": unwrapped_node_states,
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
    
    new_snapshot = StateSnapshot.model_validate(filtered_snapshot_data)
    
    return (new_snapshot, unwrapped_lore)



# --- Section 3: FastAPI 依赖注入函数  ---

def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    return request.app.state.snapshot_store