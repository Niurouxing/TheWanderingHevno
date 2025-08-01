# tests/test_03_engine_integration.py
import pytest
from uuid import uuid4

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection


@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，使用新的宏系统。"""

    
    async def test_engine_linear_flow(self, test_engine, linear_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "A" in output and "output" in output["A"]
        assert output["A"]["output"] == "a story about a cat"
        
        assert "B" in output and "llm_output" in output["B"]
        b_prompt = "The story is: a story about a cat"
        assert output["B"]["llm_output"] == f"[MOCK RESPONSE for mock/model] - Prompt received: '{b_prompt[:50]}...'"

        assert "C" in output and "llm_output" in output["C"]
        c_prompt = output['B']['llm_output']
        assert output["C"]["llm_output"] == f"[MOCK RESPONSE for mock/model] - Prompt received: '{c_prompt[:50]}...'"

    
    async def test_engine_runtime_pipeline(self, test_engine, pipeline_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})

        assert final_snapshot.world_state["main_character"] == "Sir Reginald"

        node_a_result = final_snapshot.run_output["A"]
        
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        assert node_a_result["llm_output"] == f"[MOCK RESPONSE for mock/model] - Prompt received: '{expected_prompt[:50]}...'"

        assert node_a_result["output"] == "A secret message"


@pytest.mark.asyncio
class TestEngineStateAndMacros:
    
    async def test_world_state_persists_and_macros_read_it(self, test_engine, world_vars_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        assert final_snapshot.world_state == {"theme": "cyberpunk"}

        expected_reader_output_start = "The theme is: cyberpunk and some data from setter"
        reader_output = final_snapshot.run_output["reader"]["output"]
        assert reader_output.startswith(expected_reader_output_start)

    
    async def test_graph_evolution(self, test_engine, graph_evolution_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        new_graph_def = snapshot_after_evolution.graph_collection
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"

    
    async def test_execute_runtime_integration(self, test_engine, execute_runtime_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["player_status"] == "empowered"

@pytest.mark.asyncio
class TestEngineErrorHandling:
    
    async def test_engine_detects_cycle(self, test_engine, cyclic_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})

    
    async def test_engine_handles_failure_and_skips_downstream(self, test_engine, failing_node_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "error" not in output["A_ok"]
        assert "error" not in output["D_independent"]

        assert "error" in output["B_fail"]
        assert "non_existent_variable" in output["B_fail"]["error"]

        assert "status" in output["C_skip"] and output["C_skip"]["status"] == "skipped"
        assert "reason" in output["C_skip"] and output["C_skip"]["reason"] == "Upstream failure of node B_fail."

@pytest.mark.asyncio
class TestAdvancedMacroIntegration:
    """测试引擎中更高级的宏功能，如动态函数定义和二次求值链。"""

    
    async def test_dynamic_function_definition_and_usage(self, test_engine, advanced_macro_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        assert "math_utils" in final_snapshot.world_state
        assert callable(final_snapshot.world_state["math_utils"]["hypot"])

        run_output = final_snapshot.run_output
        assert "use_skill" in run_output
        assert run_output["use_skill"]["output"] == 5.0

    
    async def test_llm_code_generation_and_execution(self, test_engine, advanced_macro_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        assert run_output["llm_propose_change"]["output"] == "world.game_difficulty = 'hard'"
        assert "execute_change" in run_output
        assert final_snapshot.world_state["game_difficulty"] == "hard"

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.call)。"""

    
    async def test_basic_subgraph_call(self, test_engine, subgraph_call_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
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
        
    
    async def test_nested_subgraph_call(self, test_engine, nested_subgraph_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=nested_subgraph_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        output = final_snapshot.run_output

        sub1_result = output["main_caller"]["output"]
        sub2_result = sub1_result["sub1_caller"]["output"]
        final_output = sub2_result["final_processor"]["output"]
        
        assert final_output == "Reached level 2 from: level 0"

    
    async def test_call_to_nonexistent_subgraph_fails_node(self, test_engine, subgraph_call_to_nonexistent_graph_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=subgraph_call_to_nonexistent_graph_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        bad_caller_result = output["bad_caller"]
        
        assert "error" in bad_caller_result
        error_message = bad_caller_result["error"]
        assert "Failed at step 1 ('system.call')" in error_message
        assert "Graph 'i_do_not_exist' not found" in error_message

    
    async def test_subgraph_can_modify_world_state(self, test_engine, subgraph_modifies_world_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_modifies_world_collection,
            world_state={"counter": 100}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        assert final_snapshot.world_state["counter"] == 110

        reader_output = final_snapshot.run_output["reader"]["output"]
        assert "Final counter: 110" in reader_output
        assert "incrementer" in reader_output
    
    
    async def test_subgraph_failure_propagates_to_caller(self, test_engine, subgraph_with_failure_collection: GraphCollection):
        # --- 测试逻辑保持不变，但对断言行为的解释被保留和强调 ---
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_with_failure_collection,
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        
        # 1. 验证调用节点本身成功，因为它成功地“捕获”了子图的运行结果
        # 这个断言是正确的，因为 system.call 本身没有抛出异常
        assert "error" not in output["caller"]
        
        # 2. 验证调用节点的输出包含了子图失败的结果
        caller_result = output["caller"]["output"]
        assert "B_fail" in caller_result
        assert "error" in caller_result["B_fail"]
        assert "non_existent" in caller_result["B_fail"]["error"]

        # 3. 验证依赖于 caller 的下游节点被执行，而不是被跳过
        # 这是预期的行为，因为 caller 节点本身的状态是 SUCCEEDED。
        assert "downstream_of_fail" in output
        assert "error" not in output.get("downstream_of_fail", {})
        
        downstream_output = output["downstream_of_fail"]["output"]
        # 验证下游节点成功地接收了包含错误信息的字典
        assert isinstance(downstream_output._data, dict)
        assert "B_fail" in downstream_output
        assert "error" in downstream_output["B_fail"]

    
    async def test_dynamic_subgraph_call_by_macro(self, test_engine, dynamic_subgraph_call_collection: GraphCollection):
        # --- 测试逻辑保持不变 ---
        # 场景1: 调用 sub_a
        initial_snapshot_a = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_a"}
        )
        final_snapshot_a = await test_engine.step(initial_snapshot_a, {})
        output_a = final_snapshot_a.run_output["dynamic_caller"]["output"]
        assert output_a["processor_a"]["output"] == "Processed by A: dynamic data"

        # 场景2: 调用 sub_b
        initial_snapshot_b = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_b"}
        )
        final_snapshot_b = await test_engine.step(initial_snapshot_b, {})
        output_b = final_snapshot_b.run_output["dynamic_caller"]["output"]
        assert "processor_a" not in output_b
        assert output_b["processor_b"]["output"] == "Processed by B: dynamic data"