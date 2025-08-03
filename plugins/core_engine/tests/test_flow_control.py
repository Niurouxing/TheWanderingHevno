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

    async def test_call_using_field_dependency_is_correctly_inferred(
        self,
        test_engine: Tuple[ExecutionEngineInterface, Container, HookManager],
        call_collection_with_using_node_ref: GraphCollection
    ):
        """
        测试：验证当 `system.flow.call` 的 `using` 字段引用主图中的节点时，
        依赖关系能被正确推断，并且执行成功。

        这个测试确保我们对依赖解析的修改（例如，未来可能忽略 'using' 字段）
        不会破坏 `call` 运行时的基本数据流功能。
        """
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=call_collection_with_using_node_ref
        )
        
        final_snapshot = await engine.step(initial_snapshot, {})

        # 1. 确认 'caller' 节点被成功执行
        assert "caller" in final_snapshot.run_output, \
            "The 'caller' node failed to execute. This likely means the dependency on 'data_provider' was not correctly inferred."

        # 2. 深入检查结果，确认数据流是正确的
        caller_output = final_snapshot.run_output["caller"]
        subgraph_result = caller_output.get("output", {})
        
        assert "processor" in subgraph_result, "The subgraph did not return a result for the 'processor' node."
        
        processor_output = subgraph_result["processor"]["output"]
        assert processor_output == "Processed: External Data"
        
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

    async def test_map_with_collect_referencing_subgraph_node(
        self, 
        test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], 
        map_collection_with_collect_and_subgraph_node_ref: GraphCollection
    ):
        """
        测试：验证当 `collect` 宏引用子图内部节点时，依赖解析器不会错误地
        将其识别为主图依赖，从而导致引擎调度失败。
        
        这个测试用例专门用于复现并验证一个已知的 Bug。
        在 Bug 修复前，此测试会因 KeyError (run_output 为空) 而失败。
        """
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=map_collection_with_collect_and_subgraph_node_ref
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        
        # 在 Bug 状态下，final_snapshot.run_output 会是 {}
        # 修复后，它应该包含 'mapper' 节点的结果
        assert "mapper" in final_snapshot.run_output, \
            "Engine failed to execute the 'mapper' node, likely due to incorrect dependency parsing."
            
        map_result = final_snapshot.run_output["mapper"]["output"]
        
        # 验证最终聚合的结果是否正确
        expected_result = [
            "Item: apple at index 0",
            "Item: banana at index 1"
        ]
        assert map_result == expected_result