# backend/core/types.py 
from __future__ import annotations
import json 
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

class ExecutionContext(BaseModel):
    initial_snapshot: StateSnapshot
    node_states: Dict[str, Any] = Field(default_factory=dict)
    world_state: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    function_registry: Dict[str, Callable] = Field(default_factory=dict)
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,
    })
    
    internal_vars: Dict[str, Any] = Field(default_factory=dict, repr=False)

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_snapshot(cls, snapshot: StateSnapshot, run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
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
        current_graphs = self.initial_snapshot.graph_collection
        if '__graph_collection__' in self.world_state:
            try:
                evolved_graph_value = self.world_state['__graph_collection__']
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
            world_state=self.world_state,
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )
        
ExecutionContext.model_rebuild()