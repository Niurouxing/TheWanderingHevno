# tests/test_03_engine_integration.py
import pytest
from uuid import uuid4

# ---------------------------------------------------------------------------
# 导入被测试的类和所需的 Fixtures
# ---------------------------------------------------------------------------
from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

# 注意：这个文件中的测试函数会自动接收来自 conftest.py 的 fixtures，
# 例如 test_engine, linear_collection, parallel_collection 等。

# ---------------------------------------------------------------------------
# Section 1: Core Execution Flow Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行和管道，使用新的宏系统。"""

    async def test_engine_linear_flow(self, test_engine: ExecutionEngine, linear_collection: GraphCollection):
        """测试简单的线性工作流 A -> B -> C，验证数据在宏之间正确传递。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        assert "A" in run_output
        assert run_output["A"]["output"] == "a story about a cat"
        
        assert "B" in run_output
        expected_prompt_b = "The story is: a story about a cat"
        # 验证宏已执行，prompt 字段是最终结果
        assert run_output["B"]["prompt"] == expected_prompt_b
        assert run_output["B"]["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt_b}]"
        
        assert "C" in run_output
        expected_prompt_c = run_output["B"]["llm_output"]
        assert run_output["C"]["prompt"] == expected_prompt_c
        assert run_output["C"]["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt_c}]"

    async def test_engine_parallel_flow(self, test_engine: ExecutionEngine, parallel_collection: GraphCollection):
        """测试并行分支的图，验证扇出和扇入。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=parallel_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        assert len(run_output) == 3
        # 验证 merger 节点，它的 merged_value 字段应该已经被宏计算好
        assert run_output["merger"]["merged_value"] == "Merged: Value A and Value B"

    async def test_engine_runtime_pipeline(self, test_engine: ExecutionEngine, pipeline_collection: GraphCollection):
        """测试单个节点内的运行时管道，并验证宏预处理与运行时的交互。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 验证 world_state 被 set_world_var 运行时修改
        assert final_snapshot.world_state["main_character"] == "The brave knight, Sir Reginald"

        # 验证 llm.default 运行时使用了被修改后的 world_state
        run_output = final_snapshot.run_output
        node_a_result = run_output["A"]
        
        expected_prompt = "Tell a story about The brave knight, Sir Reginald."
        assert node_a_result["prompt"] == expected_prompt
        assert node_a_result["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"


# ---------------------------------------------------------------------------
# Section 2: State and Macro Advanced Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineStateAndMacros:
    """测试引擎如何处理持久化状态，以及更高级的宏功能。"""

    async def test_world_state_persists_and_macros_read_it(self, test_engine: ExecutionEngine, world_vars_collection: GraphCollection):
        """验证 world_state 能被设置，并能被后续节点的宏读取。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        
        snapshot_after_set = await test_engine.step(initial_snapshot, {})
        
        assert snapshot_after_set.world_state == {"theme": "cyberpunk"}
        # 验证 reader 节点通过宏成功读取了 world_state
        assert snapshot_after_set.run_output["reader"]["output"] == "The theme is: cyberpunk"

    async def test_graph_evolution(self, test_engine: ExecutionEngine, graph_evolution_collection: GraphCollection):
        """高级测试：验证图可以修改自己的逻辑并影响后续执行。此测试逻辑不变。"""
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        assert "__graph_collection__" in snapshot_after_evolution.world_state
        
        new_graph_def = snapshot_after_evolution.graph_collection
        assert len(new_graph_def.root["main"].nodes) == 1
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})

        run_output = final_snapshot.run_output
        assert "new_node" in run_output
        assert run_output["new_node"]["output"] == "This is the evolved graph!"

    async def test_execute_runtime_integration(self, test_engine: ExecutionEngine, execute_runtime_collection: GraphCollection):
        """集成测试：验证 system.execute 能在引擎流程中正确执行二次求值。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )

        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 验证 B_execute_code 的输出
        run_output = final_snapshot.run_output
        # 副作用宏返回 None
        assert run_output["B_execute_code"]["output"] is None

        # 最关键的验证：world_state 是否被二次求值的代码所修改
        assert final_snapshot.world_state["player_status"] == "empowered"

# ---------------------------------------------------------------------------
# Section 3: Error and Edge Case Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineErrorHandling:
    """测试引擎在错误和边界情况下的鲁棒性。"""

    async def test_engine_detects_cycle(self, test_engine: ExecutionEngine, cyclic_collection: GraphCollection):
        """测试引擎在图运行初始化时能正确检测到环路。此测试逻辑不变。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})

    async def test_engine_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngine, failing_node_collection: GraphCollection):
        """测试当一个节点因宏执行失败时，下游节点被正确跳过。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output

        # 验证成功和独立的节点
        assert "error" not in run_output.get("A_ok", {})
        assert "error" not in run_output.get("D_independent", {})
        assert run_output["D_independent"]["output"] == "independent"

        # 验证失败的节点
        assert "error" in run_output.get("B_fail", {})
        # 错误原因现在是宏预处理失败
        assert run_output["B_fail"]["failed_step"] == "pre-processing"
        # 错误信息现在是 Python 的 NameError
        assert "Macro evaluation failed" in run_output["B_fail"]["error"]
        assert "name 'non_existent_variable' is not defined" in run_output["B_fail"]["error"]
        
        # 验证被跳过的下游节点
        assert "status" in run_output.get("C_skip", {})
        assert run_output["C_skip"]["status"] == "skipped"
        assert run_output["C_skip"]["reason"] == "Upstream failure of node B_fail."