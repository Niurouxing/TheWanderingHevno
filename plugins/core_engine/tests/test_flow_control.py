import pytest
from typing import Tuple

# --- 【新】导入 Sandbox 模型 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.flow.call)。"""

    async def test_basic_subgraph_call(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_call_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中设置子图需要的状态
        sandbox = sandbox_factory(
            graph_collection=subgraph_call_collection,
            initial_moment={"global_setting": "Alpha"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        # Assert
        output = final_snapshot.run_output
        processor_output = output["main_caller"]["output"]["processor"]["output"]
        assert processor_output == "Processed: Hello from main with world state: Alpha"
        
    async def test_nested_subgraph_call(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        nested_subgraph_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=nested_subgraph_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        final_output = output["main_caller"]["output"]["sub1_caller"]["output"]["final_processor"]["output"]
        assert final_output == "Reached level 2 from: level 0"

    async def test_subgraph_can_modify_moment_state(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_modifies_world_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = sandbox_factory(
            graph_collection=subgraph_modifies_world_collection,
            initial_moment={"counter": 100}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        # Assert: 检查 moment 作用域的状态是否被子图修改
        assert final_snapshot.moment["counter"] == 110
        assert "Final counter: 110" in final_snapshot.run_output["reader"]["output"]

    async def test_subgraph_failure_propagates_to_caller(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_with_failure_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=subgraph_with_failure_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        caller_result = final_snapshot.run_output["caller"]["output"]
        # 子图执行失败，其内部节点的结果会被包装在 caller 的输出中
        assert "error" in caller_result["B_fail"]

    async def test_dynamic_subgraph_call(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        dynamic_subgraph_call_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 将动态图名设置在 lore 中，因为它更像一个配置
        sandbox = sandbox_factory(
            graph_collection=dynamic_subgraph_call_collection,
            initial_lore={"target_graph": "sub_b"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert
        processor_output = final_snapshot.run_output["dynamic_caller"]["output"]["processor_b"]["output"]
        assert processor_output == "Processed by B: dynamic data"

    async def test_call_to_nonexistent_graph_fails_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_call_to_nonexistent_graph_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=subgraph_call_to_nonexistent_graph_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        assert "error" in final_snapshot.run_output["bad_caller"]
        assert "Graph 'i_do_not_exist' not found" in final_snapshot.run_output["bad_caller"]["error"]

    async def test_call_using_field_dependency_is_correctly_inferred(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        call_collection_with_using_node_ref: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=call_collection_with_using_node_ref)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        assert "caller" in final_snapshot.run_output
        caller_output = final_snapshot.run_output["caller"]
        subgraph_result = caller_output.get("output", {})
        assert "processor" in subgraph_result
        processor_output = subgraph_result["processor"]["output"]
        assert processor_output == "Processed: External Data"
        
@pytest.mark.asyncio
class TestEngineMapExecution:
    """对 system.flow.map 运行时的集成测试。"""

    async def test_basic_map(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_basic: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=map_collection_basic)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        map_result = final_snapshot.run_output["map_node"]["output"]
        assert isinstance(map_result, list) and len(map_result) == 2
        assert "generate_bio" in map_result[0]
        assert map_result[0]["generate_bio"]["output"] == "Bio for Aragorn"
        assert map_result[1]["generate_bio"]["output"] == "Bio for Gandalf"

    async def test_map_with_collect(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_with_collect: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=map_collection_with_collect)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        map_result = final_snapshot.run_output["map_node"]["output"]
        assert map_result == ["Bio for Aragorn", "Bio for Gandalf"]

    async def test_map_handles_partial_failures_gracefully(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_with_failure: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=map_collection_with_failure)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        map_result = final_snapshot.run_output["mapper"]["output"]
        
        assert len(map_result) == 3
        assert "error" not in map_result[0]["get_name"]
        assert "error" not in map_result[2]["get_name"]
        
        failed_item_result = map_result[1]
        assert "error" in failed_item_result["get_name"]
        assert "AttributeError" in failed_item_result["get_name"]["error"]

    async def test_map_with_collect_referencing_subgraph_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
        sandbox_factory: callable,
        map_collection_with_collect_and_subgraph_node_ref: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=map_collection_with_collect_and_subgraph_node_ref)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
            
        assert "mapper" in final_snapshot.run_output
        map_result = final_snapshot.run_output["mapper"]["output"]
        
        expected_result = [
            "Item: apple at index 0",
            "Item: banana at index 1"
        ]
        assert map_result == expected_result