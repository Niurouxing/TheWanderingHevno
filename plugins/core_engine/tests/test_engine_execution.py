# plugins/core_engine/tests/test_engine_execution.py

import pytest
from uuid import uuid4

# 从平台核心契约导入共享的数据模型
from backend.core.contracts import StateSnapshot, GraphCollection

# 从本插件的接口定义导入，测试应依赖于接口而非具体实现
from plugins.core_engine.interfaces import ExecutionEngineInterface

# 使用 pytest.mark.asyncio 来标记所有异步测试
@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行、错误处理等。"""

    async def test_linear_flow(self, test_engine: ExecutionEngineInterface, linear_collection: GraphCollection):
        """测试一个简单的线性依赖图 A -> B -> C。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "A" in output and "output" in output["A"]
        assert "B" in output and "llm_output" in output["B"]
        assert "C" in output and "llm_output" in output["C"]
        
        # 验证B的输入来自A
        b_prompt = "The story is: a story about a cat"
        assert output["B"]["llm_output"].startswith(f"[MOCK RESPONSE for mock/model] - Prompt received: '{b_prompt[:50]}...'")

        # 验证C的输入来自B
        c_prompt = output['B']['llm_output']
        assert output["C"]["llm_output"].startswith(f"[MOCK RESPONSE for mock/model] - Prompt received: '{c_prompt[:50]}...'")

    async def test_parallel_flow(self, test_engine: ExecutionEngineInterface, parallel_collection: GraphCollection):
        """测试一个扇出再扇入的图 (A, B) -> C，验证并行执行和依赖合并。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=parallel_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        assert "source_A" in output
        assert "source_B" in output
        assert "merger" in output

        assert output["merger"]["output"] == "Merged: Value A and Value B"

    async def test_pipeline_within_node(self, test_engine: ExecutionEngineInterface, pipeline_collection: GraphCollection):
        """测试节点内指令管道，后一个指令可以使用前一个指令的输出 (`pipe` 对象)。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 验证第一个指令设置的世界变量
        assert final_snapshot.world_state["main_character"] == "Sir Reginald"

        node_a_result = final_snapshot.run_output["A"]
        
        # 验证第三个指令的 prompt 正确使用了 world 状态和第二个指令的 pipe 输出
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        assert node_a_result["llm_output"].startswith(f"[MOCK RESPONSE for mock/model] - Prompt received: '{expected_prompt[:50]}...'")
        
        # 验证第二个指令的输出也被保留在最终结果中
        assert node_a_result["output"] == "A secret message"
        
    async def test_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngineInterface, failing_node_collection: GraphCollection):
        """测试当一个节点失败时，其下游依赖节点会被正确跳过。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        # 验证成功的节点
        assert "error" not in output["A_ok"]
        assert "error" not in output["D_independent"]

        # 验证失败的节点
        assert "error" in output["B_fail"]
        assert "non_existent_variable" in output["B_fail"]["error"]

        # 验证被跳过的节点
        assert "status" in output["C_skip"] and output["C_skip"]["status"] == "skipped"
        assert "reason" in output["C_skip"] and "Upstream failure of node B_fail" in output["C_skip"]["reason"]

    async def test_detects_cycle(self, test_engine: ExecutionEngineInterface, cyclic_collection: GraphCollection):
        """测试引擎能否在执行前检测到图中的依赖环。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})


    async def test_subgraph_call(self, test_engine: ExecutionEngineInterface, subgraph_call_collection: GraphCollection):
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        subgraph_result = output["main_caller"]["output"]
        processor_output = subgraph_result["processor"]["output"]
        assert processor_output == "Processed: Hello from main with world state: Alpha"

    async def test_subgraph_failure_propagates_to_caller(self, test_engine, subgraph_with_failure_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_with_failure_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        caller_result = output["caller"]["output"]
        assert "error" in caller_result["B_fail"]

@pytest.mark.asyncio
class TestEngineStateManagement:
    """测试与状态管理（世界状态、图演化）相关的引擎功能。"""

    async def test_world_state_persists_and_macros_read_it(self, test_engine: ExecutionEngineInterface, world_vars_collection: GraphCollection):
        """测试 `set_world_var` 能够修改状态，且后续节点能通过宏读取到该状态。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        assert final_snapshot.world_state.get("theme") == "cyberpunk"

        reader_output = final_snapshot.run_output["reader"]["output"]
        assert reader_output.startswith("The theme is: cyberpunk")

    async def test_graph_evolution(self, test_engine: ExecutionEngineInterface, graph_evolution_collection: GraphCollection):
        """测试图本身作为状态可以被逻辑修改（图演化）。"""
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        
        # 第一次执行，图演化节点运行，修改 world.__graph_collection__
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        # 验证新生成的快照中，图的定义已经改变
        new_graph_def = snapshot_after_evolution.graph_collection
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        # 第二次执行，应该在新图上运行
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"

    async def test_execute_runtime_modifies_state(self, test_engine: ExecutionEngineInterface, execute_runtime_collection: GraphCollection):
        """测试 `system.execute` 运行时可以成功执行宏并修改世界状态。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["player_status"] == "empowered"

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.call)。"""

    async def test_basic_subgraph_call(self, test_engine: ExecutionEngineInterface, subgraph_call_collection: GraphCollection):
        """测试基本的子图调用，包括输入映射和世界状态访问。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output
        
        subgraph_result = output["main_caller"]["output"]
        assert isinstance(subgraph_result, dict)
        
        processor_output = subgraph_result["processor"]["output"]
        expected_str = "Processed: Hello from main with world state: Alpha"
        assert processor_output == expected_str
        
    async def test_nested_subgraph_call(self, test_engine: ExecutionEngineInterface, nested_subgraph_collection: GraphCollection):
        """测试嵌套的子图调用：main -> sub1 -> sub2。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=nested_subgraph_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output

        sub1_result = output["main_caller"]["output"]
        sub2_result = sub1_result["sub1_caller"]["output"]
        final_output = sub2_result["final_processor"]["output"]
        
        assert final_output == "Reached level 2 from: level 0"

    async def test_subgraph_can_modify_world_state(self, test_engine: ExecutionEngineInterface, subgraph_modifies_world_collection: GraphCollection):
        """测试子图可以修改世界状态，且父图中的后续节点可以读取到。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_modifies_world_collection,
            world_state={"counter": 100}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        assert final_snapshot.world_state["counter"] == 110

        reader_output = final_snapshot.run_output["reader"]["output"]
        assert "Final counter: 110" in reader_output

    async def test_subgraph_failure_propagates_to_caller(self, test_engine: ExecutionEngineInterface, subgraph_with_failure_collection: GraphCollection):
        """
        测试子图内部的失败会体现在调用节点的输出中。
        重要：调用节点本身 (`caller`) 应为 SUCCEEDED，因为它成功“执行”并捕获了子图的结果（即使结果是失败）。
        """
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_with_failure_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        
        # 1. 调用节点本身没有错误
        assert "error" not in output["caller"]
        
        # 2. 调用节点的输出包含了子图的失败信息
        caller_result = output["caller"]["output"]
        assert "B_fail" in caller_result
        assert "error" in caller_result["B_fail"]
        assert "non_existent" in caller_result["B_fail"]["error"]

        # 3. 依赖于 `caller` 的下游节点会执行，因为它看到 `caller` 是成功的
        assert "downstream_of_fail" in output
        assert "error" not in output.get("downstream_of_fail", {})

@pytest.mark.asyncio
class TestEngineMapExecution:
    """对 system.map 运行时的集成测试。"""
    
    async def test_basic_map(self, test_engine: ExecutionEngineInterface, map_collection_basic: GraphCollection):
        """测试基本的 scatter-gather 功能，不使用 `collect`。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_basic)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        map_result = final_snapshot.run_output["character_processor_map"]["output"]

        assert isinstance(map_result, list) and len(map_result) == 3
        assert "generate_bio" in map_result[0]
        assert "Aragorn" in map_result[0]["generate_bio"]["llm_output"] and "Index: 0" in map_result[0]["generate_bio"]["llm_output"]
        assert "Legolas" in map_result[2]["generate_bio"]["llm_output"] and "Index: 2" in map_result[2]["generate_bio"]["llm_output"]

    async def test_map_with_collect(self, test_engine: ExecutionEngineInterface, map_collection_with_collect: GraphCollection):
        """测试 `collect` 功能，期望输出是一个扁平化的值列表。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_with_collect)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        map_result = final_snapshot.run_output["character_processor_map"]["output"]

        assert isinstance(map_result, list) and len(map_result) == 3
        assert isinstance(map_result[0], str)
        assert map_result[0].startswith("[MOCK RESPONSE") and "Aragorn" in map_result[0]

    async def test_map_handles_concurrent_world_writes(self, test_engine: ExecutionEngineInterface, map_collection_concurrent_write: GraphCollection):
        """验证在 map 中并发写入 world_state 是原子和安全的。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 10个并行任务，每个增加10金币
        expected_gold = 100
        assert final_snapshot.world_state.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold

    async def test_map_handles_partial_failures_gracefully(self, test_engine: ExecutionEngineInterface, map_collection_with_failure: GraphCollection):
        """测试当 map 迭代中的某些子图失败时，整体操作不会崩溃，并返回清晰的结果。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=map_collection_with_failure)
        final_snapshot = await test_engine.step(initial_snapshot, {})

        map_result = final_snapshot.run_output["mapper"]["output"]

        assert len(map_result) == 3
        # 验证成功的项 (Alice, Charlie)
        assert "error" not in map_result[0].get("get_name", {})
        assert "error" not in map_result[2].get("get_name", {})

        # 验证失败的项 (Bob)
        failed_item_result = map_result[1]
        assert "error" in failed_item_result["get_name"]
        assert "AttributeError" in failed_item_result["get_name"]["error"]