# plugins/core_engine/tests/test_flow_control.py
import pytest
from typing import Tuple

# --- 核心导入 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """【集成测试】测试引擎的子图执行功能 (system.flow.call)。"""

    async def test_basic_subgraph_call_with_using_and_moment(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_call_collection: GraphCollection
    ):
        """测试：子图能同时访问 `using` 传入的参数和共享的 `moment` 状态。"""
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中设置子图需要的共享状态。
        sandbox = await sandbox_factory(
            graph_collection=subgraph_call_collection,
            initial_moment={"global_setting": "Alpha"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # Assert (Output): 验证子图的输出结合了 `using` 输入和 `moment` 状态。
        output = final_snapshot.run_output
        # 子图的结果被嵌套在调用节点的输出中
        processor_output = output["main_caller"]["output"]["processor"]["output"]
        assert processor_output == "Processed: Hello from main with world state: Alpha"
        
    async def test_nested_subgraph_call(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        nested_subgraph_collection: GraphCollection
    ):
        """测试：一个子图可以调用另一个子图，形成调用链。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=nested_subgraph_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        output = final_snapshot.run_output
        final_output = output["main_caller"]["output"]["sub1_caller"]["output"]["final_processor"]["output"]
        assert final_output == "Reached level 2 from: level 0"

    async def test_subgraph_can_modify_moment_state(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_modifies_world_collection: GraphCollection
    ):
        """【关键测试】验证子图内的操作可以修改 `moment` 状态，并影响到主图中的后续节点。"""
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = await sandbox_factory(
            graph_collection=subgraph_modifies_world_collection,
            initial_moment={"counter": 100}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # Assert (State): 检查最终快照的 `moment` 作用域，验证状态是否被子图修改。
        assert final_snapshot.moment["counter"] == 110
        # Assert (Output): 检查主图中依赖于此状态的后续节点是否读取到了正确的值。
        assert "Final counter: 110" in final_snapshot.run_output["reader"]["output"]

    async def test_subgraph_failure_propagates_to_caller(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_with_failure_collection: GraphCollection
    ):
        """测试：如果子图中的一个节点失败，该失败信息会包含在调用节点的输出中。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=subgraph_with_failure_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        caller_result = final_snapshot.run_output["caller"]["output"]
        # 子图执行失败，其内部节点的结果会被包装在 caller 的输出中
        assert "error" in caller_result["B_fail"]

    async def test_dynamic_subgraph_call_from_lore(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        dynamic_subgraph_call_collection: GraphCollection
    ):
        """测试：调用的图名称可以通过宏从 `lore` 作用域动态获取。"""
        engine, container, _ = test_engine_setup
        
        # Arrange: 将动态图名设置在 lore 中，因为它更像一个不应被回滚的配置。
        sandbox = await sandbox_factory(
            graph_collection=dynamic_subgraph_call_collection,
            initial_lore={"target_graph": "sub_b"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output): 验证最终调用的是 sub_b 而不是 sub_a。
        processor_output = final_snapshot.run_output["dynamic_caller"]["output"]["processor_b"]["output"]
        assert processor_output == "Processed by B: dynamic data"

    async def test_call_to_nonexistent_graph_fails_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        subgraph_call_to_nonexistent_graph_collection: GraphCollection
    ):
        """测试：调用一个不存在的子图会导致调用节点本身失败。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=subgraph_call_to_nonexistent_graph_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        assert "error" in final_snapshot.run_output["bad_caller"]
        assert "Graph 'i_do_not_exist' not found" in final_snapshot.run_output["bad_caller"]["error"]

    async def test_call_using_field_dependency_is_correctly_inferred(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        call_collection_with_using_node_ref: GraphCollection
    ):
        """测试：当 `using` 字段引用另一个节点时，依赖关系被正确推断。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=call_collection_with_using_node_ref)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # Assert (Output)
        assert "caller" in final_snapshot.run_output
        caller_output = final_snapshot.run_output["caller"]["output"]
        assert "processor" in caller_output
        assert caller_output["processor"]["output"] == "Processed: External Data"
        

@pytest.mark.asyncio
class TestEngineMapExecution:
    """【集成测试】对 system.flow.map 运行时的集成测试。"""

    async def test_basic_map(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_basic: GraphCollection
    ):
        """测试 `map` 的基本功能：为列表中的每个元素并行执行子图。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=map_collection_basic)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
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
        """测试 `map` 的 `collect` 功能：从每次子图运行中提取特定结果并汇集成一个列表。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=map_collection_with_collect)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # Assert (Output)
        map_result = final_snapshot.run_output["map_node"]["output"]
        assert map_result == ["Bio for Aragorn", "Bio for Gandalf"]

    async def test_map_handles_partial_failures_gracefully(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_with_failure: GraphCollection
    ):
        """测试当部分迭代失败时，`map` 依然能返回所有迭代的结果，并包含错误信息。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=map_collection_with_failure)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        map_result = final_snapshot.run_output["mapper"]["output"]
        
        assert len(map_result) == 3
        # 验证成功的迭代
        assert "error" not in map_result[0]["get_name"]
        assert "error" not in map_result[2]["get_name"]
        
        # 验证失败的迭代包含了错误信息
        failed_item_result = map_result[1]
        assert "error" in failed_item_result["get_name"]
        assert "AttributeError" in failed_item_result["get_name"]["error"]

    async def test_map_with_collect_referencing_subgraph_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
        sandbox_factory: callable,
        map_collection_with_collect_and_subgraph_node_ref: GraphCollection
    ):
        """测试 `collect` 宏可以正确引用子图内部的节点 (`nodes.xxx`)。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=map_collection_with_collect_and_subgraph_node_ref)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
            
        # Assert (Output)
        assert "mapper" in final_snapshot.run_output
        map_result = final_snapshot.run_output["mapper"]["output"]
        
        expected_result = [
            "Item: apple at index 0",
            "Item: banana at index 1"
        ]
        assert map_result == expected_result