# plugins/core_engine/tests/test_engine_execution.py
import pytest
from uuid import uuid4
from typing import Tuple

from plugins.core_engine.contracts import StateSnapshot, GraphCollection, ExecutionEngineInterface
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行、错误处理等。"""

    async def test_linear_flow(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], linear_collection: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "C" in output and "llm_output" in output["C"]
        assert "The story is: a story about a cat" in output["B"]["llm_output"]

    async def test_parallel_flow(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], parallel_collection: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=parallel_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        assert final_snapshot.run_output["merger"]["output"] == "Merged: Value A and Value B"

    async def test_pipeline_within_node(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], pipeline_collection: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        final_snapshot = await engine.step(initial_snapshot, {})

        assert final_snapshot.world_state["main_character"] == "Sir Reginald"
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        assert expected_prompt in final_snapshot.run_output["A"]["llm_output"]
        
    async def test_handles_failure_and_skips_downstream(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], failing_node_collection: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "error" in output["B_fail"]
        assert "status" in output["C_skip"] and output["C_skip"]["status"] == "skipped"

@pytest.mark.asyncio
class TestEngineStateManagement:
    """测试与状态管理（世界状态、图演化）相关的引擎功能。"""

    async def test_world_state_persists(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], world_vars_collection: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        
        assert final_snapshot.world_state.get("theme") == "cyberpunk"
        assert final_snapshot.run_output["reader"]["output"] == "The theme is: cyberpunk"

    async def test_graph_evolution(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], graph_evolution_collection: GraphCollection):
        engine, _, _ = test_engine
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        
        snapshot_after_evolution = await engine.step(genesis_snapshot, {})
        
        new_graph_def = snapshot_after_evolution.graph_collection
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        final_snapshot = await engine.step(snapshot_after_evolution, {})
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"