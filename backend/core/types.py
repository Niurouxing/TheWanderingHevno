# backend/core/types.py 
from __future__ import annotations
import json 
import asyncio # <-- 需要导入 asyncio 来处理锁
from typing import Dict, Any, Callable, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection
from backend.core.utils import DotAccessibleDict

ServiceRegistry = Dict[str, Any]

class SharedContext(BaseModel):
    """
    一个封装了所有图执行期间共享资源的对象。
    """
    world_state: Dict[str, Any]
    session_info: Dict[str, Any]
    global_write_lock: asyncio.Lock
    # 【核心修改】用一个通用的服务容器替代了特定的 llm_service
    services: DotAccessibleDict

    model_config = {"arbitrary_types_allowed": True}

class ExecutionContext(BaseModel):
    """
    代表一个【单次图执行】的上下文。
    它包含私有状态（如 node_states）和对全局共享状态的引用。
    """
    # --- 私有状态 (Per-Graph-Run State) ---
    # 每次调用 execute_graph 时，都会为这次运行创建一个新的 ExecutionContext
    # 这确保了 node_states 是隔离的。
    node_states: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    # --- 共享状态 (Shared State) ---
    # 这不是一个副本，而是对一个共享对象的引用。
    shared: SharedContext
    initial_snapshot: StateSnapshot # 引用初始快照以获取图定义等信息

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def create_for_main_run(
        cls, 
        snapshot: StateSnapshot, 
        # 【核心修改】接收一个服务注册表，而不是某个特定服务
        services: ServiceRegistry, 
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
            # 将传入的服务注册表包装成可点访问的字典，并存入共享上下文
            services=DotAccessibleDict(services)
        )
        return cls(
            shared=shared_context,
            initial_snapshot=snapshot,
            run_vars=run_vars or {}
        )

    @classmethod
    def create_for_sub_run(cls, parent_context: 'ExecutionContext', run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        """
        为子图（由 call/map 调用）创建一个新的执行上下文。
        关键在于它【共享】父上下文的 `shared` 对象。
        """
        return cls(
            # 传递对同一个共享对象的引用
            shared=parent_context.shared,
            # 初始快照和图定义保持不变
            initial_snapshot=parent_context.initial_snapshot,
            # 子运行可以有自己的 run_vars，例如 map 迭代时的 item
            run_vars=run_vars or {}
            # 注意：node_states 会自动被 Pydantic 创建为一个新的空字典，实现了隔离！
        )

    def to_next_snapshot(
        self,
        final_node_states: Dict[str, Any],
        triggering_input: Dict[str, Any]
    ) -> StateSnapshot:
        """从当前上下文的状态生成下一个快照。"""
        # 从共享状态中获取最终的世界状态
        final_world_state = self.shared.world_state
        
        current_graphs = self.initial_snapshot.graph_collection
        # 检查世界状态中是否有演化的图定义
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

        return StateSnapshot(
            sandbox_id=self.initial_snapshot.sandbox_id,
            graph_collection=current_graphs,
            world_state=final_world_state, # 使用最终的世界状态
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )

# 重建模型以确保所有引用都已解析
SharedContext.model_rebuild()
ExecutionContext.model_rebuild()