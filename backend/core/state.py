# backend/core/state.py

from __future__ import annotations
from fastapi import Request
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, ValidationError


from backend.core.hooks import HookManager
from backend.core.plugin_types import BeforeSnapshotCreateContext
from backend.core.models import GraphCollection
from backend.core.utils import DotAccessibleDict

# --- 1. 持久化状态模型 (原 state_models.py) ---
# 这些模型定义了存储在数据库或内存中的长期状态

class StateSnapshot(BaseModel):
    """
    一个不可变的快照，代表 Sandbox 在某个时间点的完整状态。
    """
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
    """
    一个交互式模拟环境的容器。
    它管理着一系列的状态快照。
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_latest_snapshot(self, store: SnapshotStore) -> Optional[StateSnapshot]:
        if self.head_snapshot_id:
            return store.get(self.head_snapshot_id)
        return None

class SnapshotStore:
    """一个简单的内存快照存储。"""
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        if snapshot.id in self._store:
            raise ValueError(f"Snapshot with id {snapshot.id} already exists.")
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        return [s for s in self._store.values() if s.sandbox_id == sandbox_id]

    def clear(self):
        self._store = {}


# --- 2. 运行时上下文模型 (原 types.py) ---
# 这些模型定义了在单次图执行期间，存在于内存中的临时状态和上下文


class SharedContext(BaseModel):
    """
    一个封装了所有图执行期间共享资源的对象。
    """
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    services: DotAccessibleDict

    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    """
    代表一个【单次图执行】的上下文。
    它包含私有状态（如 node_states）和对全局共享状态的引用。
    """
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    shared: SharedContext
    initial_snapshot: StateSnapshot # 引用初始快照以获取图定义等信息
    hook_manager: HookManager

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def create_for_main_run(
        cls, 
        snapshot: StateSnapshot,
        services: Dict[str, Any],
        hook_manager: HookManager,
        run_vars: Dict[str, Any] = None
    ) -> 'ExecutionContext':
        """为顶层图执行创建初始上下文。"""
        shared_context = SharedContext(
            world_state=snapshot.world_state.copy(),
            session_info={
                "start_time": datetime.now(timezone.utc),
                "conversation_turn": 0,
            },
            global_write_lock=asyncio.Lock(),
            services=DotAccessibleDict(services)
        )
        return cls(
            shared=shared_context,
            initial_snapshot=snapshot,
            run_vars=run_vars or {},
            hook_manager=hook_manager
        )

    @classmethod
    def create_for_sub_run(cls, parent_context: 'ExecutionContext', run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        """为子图（由 call/map 调用）创建一个新的执行上下文。"""
        return cls(
            shared=parent_context.shared,
            initial_snapshot=parent_context.initial_snapshot,
            run_vars=run_vars or {}
        )

    def to_next_snapshot(
        self,
        final_node_states: Dict[str, Any],
        triggering_input: Dict[str, Any]
    ) -> StateSnapshot:
        """从当前上下文的状态生成下一个快照。"""
        final_world_state = self.shared.world_state
        
        current_graphs = self.initial_snapshot.graph_collection
        if '__graph_collection__' in final_world_state:
            try:
                evolved_graph_value = final_world_state['__graph_collection__']
                if isinstance(evolved_graph_value, str):
                    evolved_graph_dict = json.loads(evolved_graph_value)
                else:
                    evolved_graph_dict = evolved_graph_value
                
                evolved_graphs = GraphCollection.model_validate(evolved_graph_dict)
                current_graphs = evolved_graphs
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

        snapshot_data = {
            "sandbox_id": self.initial_snapshot.sandbox_id,
            "graph_collection": current_graphs,
            "world_state": final_world_state,
            "parent_snapshot_id": self.initial_snapshot.id,
            "run_output": final_node_states,
            "triggering_input": triggering_input
        }

        filtered_snapshot_data = asyncio.run( # 在非async函数中调用async钩子
             self.hook_manager.filter(
                "before_snapshot_create",
                snapshot_data,
                context=BeforeSnapshotCreateContext(
                    snapshot_data=snapshot_data,
                    execution_context=self
                )
            )
        )

        return StateSnapshot(**filtered_snapshot_data)



def get_sandbox_store(request: Request) -> Dict[UUID, Sandbox]:
    """依赖注入函数，用于获取沙盒存储。"""
    return request.app.state.sandbox_store

def get_snapshot_store(request: Request) -> SnapshotStore:
    """依赖注入函数，用于获取快照存储。"""
    return request.app.state.snapshot_store


# --- 3. 统一的模型重建 ---
# 确保 Pydantic 能够正确处理所有内部引用和向前引用
StateSnapshot.model_rebuild()
Sandbox.model_rebuild()
SharedContext.model_rebuild()
ExecutionContext.model_rebuild()