# plugins/core_engine/tests/test_flow_control.py
import pytest
from uuid import uuid4
from typing import Tuple

from plugins.core_engine.contracts import StateSnapshot, GraphCollection, ExecutionEngineInterface
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.flow.call)。"""

    # test_basic_subgraph_call (from previous step) remains here...
    async def test_basic_subgraph_call(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], subgraph_call_collection: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        processor_output = output["main_caller"]["output"]["processor"]["output"]
        assert processor_output == "Processed: Hello from main with world state: Alpha"
        
    async def test_nested_subgraph_call(self, test_engine, nested_subgraph_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=nested_subgraph_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        final_output = output["main_caller"]["output"]["sub1_caller"]["output"]["final_processor"]["output"]
        assert final_output == "Reached level 2 from: level 0"

    async def test_subgraph_can_modify_world_state(self, test_engine, subgraph_modifies_world_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_modifies_world_collection,
            world_state={"counter": 100}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["counter"] == 110
        assert "Final counter: 110" in final_snapshot.run_output["reader"]["output"]

    async def test_subgraph_failure_propagates_to_caller(self, test_engine, subgraph_with_failure_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_with_failure_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        caller_result = final_snapshot.run_output["caller"]["output"]
        assert "error" in caller_result["B_fail"]

    async def test_dynamic_subgraph_call(self, test_engine, dynamic_subgraph_call_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_b"}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        processor_output = final_snapshot.run_output["dynamic_caller"]["output"]["processor_b"]["output"]
        assert processor_output == "Processed by B: dynamic data"

    async def test_call_to_nonexistent_graph_fails_node(self, test_engine, subgraph_call_to_nonexistent_graph_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_call_to_nonexistent_graph_collection)
        final_snapshot = await engine.step(initial_snapshot, {})
        assert "error" in final_snapshot.run_output["bad_caller"]
        assert "Graph 'i_do_not_exist' not found" in final_snapshot.run_output["bad_caller"]["error"]


@pytest.mark.asyncio
class TestEngineMapExecution:
    """对 system.flow.map 运行时的集成测试。"""
    async def test_basic_map(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], map_collection_basic: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_basic)
        final_snapshot = await engine.step(initial_snapshot, {})
        
        map_result = final_snapshot.run_output["map_node"]["output"]
        assert isinstance(map_result, list) and len(map_result) == 2
        assert "generate_bio" in map_result[0]
        assert map_result[0]["generate_bio"]["output"] == "Bio for Aragorn"
        assert map_result[1]["generate_bio"]["output"] == "Bio for Gandalf"

    async def test_map_with_collect(self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], map_collection_with_collect: GraphCollection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_with_collect)
        final_snapshot = await engine.step(initial_snapshot, {})

        map_result = final_snapshot.run_output["map_node"]["output"]
        assert map_result == ["Bio for Aragorn", "Bio for Gandalf"]

    async def test_map_handles_partial_failures_gracefully(self, test_engine, map_collection_with_failure):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_with_failure)
        final_snapshot = await engine.step(initial_snapshot, {})
        map_result = final_snapshot.run_output["mapper"]["output"]
        
        assert len(map_result) == 3
        assert "error" not in map_result[0]["get_name"]
        assert "error" not in map_result[2]["get_name"]
        
        failed_item_result = map_result[1]
        assert "error" in failed_item_result["get_name"]
        assert "AttributeError" in failed_item_result["get_name"]["error"]