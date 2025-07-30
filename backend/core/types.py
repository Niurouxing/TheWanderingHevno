# backend/core/types.py (修正版)

from __future__ import annotations
import json 
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field 
from datetime import datetime, timezone

from backend.models import GraphCollection
# StateSnapshot 在这里被 ExecutionContext 引用，但定义在 sandbox_models.py
# sandbox_models.py 又引用了 GraphCollection，形成了循环导入的风险。
# 幸运的是，Python的模块导入机制和 Pydantic 的延迟解析通常能处理好，
# 但为了更清晰，可以把 StateSnapshot 移动到 types.py 或一个更基础的文件中。
# 不过目前问题不大，我们先解决重复字段。
from backend.core.sandbox_models import StateSnapshot 

class ExecutionContext(BaseModel):
    """
    定义一次图执行的完整上下文。
    这是一个纯数据容器，不包含执行逻辑。
    """
    initial_snapshot: StateSnapshot
    node_states: Dict[str, Any] = Field(default_factory=dict)
    world_state: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    # 合并后的定义
    function_registry: Dict[str, Callable] = Field(default_factory=dict)
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,  # 保留更完整的定义
    })

    model_config = {
        "arbitrary_types_allowed": True
    }

    @classmethod
    def from_snapshot(cls, snapshot: StateSnapshot, run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        """工厂方法：从一个快照创建执行上下文。"""
        # 将 run_vars 也作为初始化的一部分
        return cls(
            initial_snapshot=snapshot,
            world_state=snapshot.world_state.copy(),
            run_vars=run_vars or {}
        )

    def to_next_snapshot(
        self,
        final_node_states: Dict[str, Any],
        triggering_input: Dict[str, Any]
    ) -> StateSnapshot:
        """从当前上下文的状态创建下一个快照。"""
        # 你的文档中提到图可以演化，这意味着 graph_collection 应该从 world_state 中获取
        # 如果它被修改了的话。
        current_graphs = self.initial_snapshot.graph_collection
        # 这是一个示例，你可以定义一个特殊的key来存放演化后的图
        if '__graph_collection__' in self.world_state:
            try:
                # 从 world_state 获取的值可能是 JSON 字符串，需要解析。
                evolved_graph_value = self.world_state['__graph_collection__']
                if isinstance(evolved_graph_value, str):
                    evolved_graph_dict = json.loads(evolved_graph_value)
                else:
                    evolved_graph_dict = evolved_graph_value # It might already be a dict

                evolved_graphs = GraphCollection.model_validate(evolved_graph_dict)
                current_graphs = evolved_graphs
            except Exception as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

        return StateSnapshot(
            sandbox_id=self.initial_snapshot.sandbox_id,
            graph_collection=current_graphs,
            world_state=self.world_state,
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )