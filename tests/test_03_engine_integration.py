# tests/test_03_engine_integration.py
import pytest
import json

# ---------------------------------------------------------------------------
# 导入被测试的类和所需的 Fixtures
# ---------------------------------------------------------------------------
from backend.core.engine import ExecutionEngine
from backend.core.sandbox_models import StateSnapshot
from backend.models import GraphCollection

# 注意：这个文件中的测试函数会自动接收来自 conftest.py 的 fixtures，
# 例如 test_engine, linear_collection, parallel_collection 等。

# ---------------------------------------------------------------------------
# Section 1: Core Execution Flow Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行和管道。"""

    async def test_engine_linear_flow(self, test_engine: ExecutionEngine, linear_collection: GraphCollection):
        """测试简单的线性工作流 A -> B -> C，验证数据正确传递。"""
        # 创世快照
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        
        # 执行一步
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 验证结果
        run_output = final_snapshot.run_output
        assert "A" in run_output
        assert run_output["A"]["output"] == "a story about a cat"
        
        assert "B" in run_output
        assert run_output["B"]["output"] == "The story is: a story about a cat"
        
        assert "C" in run_output
        assert run_output["C"]["llm_output"] == "LLM_RESPONSE_FOR:[The story is: a story about a cat]"

    async def test_engine_parallel_flow(self, test_engine: ExecutionEngine, parallel_collection: GraphCollection):
        """测试并行分支的图，验证扇出和扇入。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=parallel_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        assert len(run_output) == 3 # source_A, source_B, merger
        expected_merged = "Merged: Value A and Value B"
        assert run_output["merger"]["output"] == expected_merged

    async def test_engine_runtime_pipeline(self, test_engine: ExecutionEngine, pipeline_collection: GraphCollection):
        """测试单个节点内的运行时管道，并验证'pipeline_state'的合并行为。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})

        run_output = final_snapshot.run_output
        assert "B" in run_output
        node_b_result = run_output["B"]
        
        expected_prompt = "Create a story about a cheerful dog."
        expected_llm_output = f"LLM_RESPONSE_FOR:[{expected_prompt}]"

        # 验证 pipeline_state 的合并行为：最终结果应包含所有步骤的输出
        assert node_b_result["template"] == "Create a story about {{ nodes.A.output }}." # from initial data
        assert node_b_result["output"] == expected_prompt  # from TemplateRuntime
        assert node_b_result["llm_output"] == expected_llm_output # from LLMRuntime


# ---------------------------------------------------------------------------
# Section 2: State Management Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineStateManagement:
    """测试引擎如何处理和演化持久化状态（world_state, graph_collection）。"""

    async def test_world_state_persists_between_steps(self, test_engine: ExecutionEngine, world_vars_collection: GraphCollection):
        """关键测试：验证 world_state 在多个 step 之间正确传递和使用。"""
        # --- Step 1: 设置 world_state ---
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        
        # 执行设置变量的图
        snapshot_after_set = await test_engine.step(genesis_snapshot, {})
        
        # 断言 world_state 在第一个快照中被正确修改
        assert snapshot_after_set.world_state == {"theme": "cyberpunk"}
        # 断言读取节点也成功了
        assert snapshot_after_set.run_output["reader"]["output"] == "The theme is: cyberpunk"

        # --- Step 2: 读取并使用已设置的 world_state ---
        # 创建一个新图，它只读取变量
        reader_only_collection = GraphCollection.model_validate({
            "main": {"nodes": [{"id": "reader_only", "data": {
                "runtime": "system.template", "template": "The persistent theme is: {{ world.theme }}"
            }}]}
        })
        
        # 创建一个新的初始快照，但这次它继承了上一步的 world_state
        # 并且使用新的图定义
        initial_snapshot_for_step2 = StateSnapshot(
            sandbox_id=genesis_snapshot.sandbox_id,
            graph_collection=reader_only_collection,
            world_state=snapshot_after_set.world_state, # 继承状态！
            parent_snapshot_id=snapshot_after_set.id
        )

        # 在新图上执行一步
        final_snapshot = await test_engine.step(initial_snapshot_for_step2, {})
        
        # 断言新图成功读取了由上一个完全不同的图执行所设置的持久化状态
        assert final_snapshot.run_output["reader_only"]["output"] == "The persistent theme is: cyberpunk"

    async def test_graph_evolution(self, test_engine: ExecutionEngine, graph_evolution_collection: GraphCollection):
        """高级测试：验证图可以修改自己的逻辑并影响后续执行。"""
        # --- Step 1: 执行图演化逻辑 ---
        # 这个图会生成一个新的图定义，并存入 world_state['__graph_collection__']
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        # 验证 world_state 中包含了新图的定义（以字符串形式）
        assert "__graph_collection__" in snapshot_after_evolution.world_state
        
        # 验证新快照的 graph_collection 自身已经被更新！
        # 这是因为 ExecutionContext.to_next_snapshot() 的逻辑
        new_graph_def = snapshot_after_evolution.graph_collection
        assert len(new_graph_def.graphs["main"].nodes) == 1
        assert new_graph_def.graphs["main"].nodes[0].id == "new_node"
        
        # --- Step 2: 使用演化后的图执行 ---
        # 引擎现在应该使用 snapshot_after_evolution 中存储的新图来执行
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})

        # 断言执行的是新图的逻辑
        run_output = final_snapshot.run_output
        assert "new_node" in run_output
        assert "graph_generator" not in run_output # 旧图的节点已经不存在了
        assert run_output["new_node"]["output"] == "This is the evolved graph!"

# ---------------------------------------------------------------------------
# Section 3: Error and Edge Case Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineErrorHandling:
    """测试引擎在错误和边界情况下的鲁棒性。"""

    async def test_engine_detects_cycle(self, test_engine: ExecutionEngine, cyclic_collection: GraphCollection):
        """测试引擎在图运行初始化时能正确检测到环路。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})

    async def test_engine_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngine, failing_node_collection: GraphCollection):
        """测试当一个节点失败时，下游节点被正确跳过，而独立分支不受影响。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output

        # 验证成功和独立的节点
        assert "error" not in run_output.get("A_ok", {})
        assert "error" not in run_output.get("D_independent", {})
        assert run_output["D_independent"]["output"] == "independent"

        # 验证失败的节点
        assert "error" in run_output.get("B_fail", {})
        assert "Failed at step 1" in run_output["B_fail"]["error"]
        assert "'undefined' is undefined" in run_output["B_fail"]["error"]
        
        # 验证被跳过的下游节点
        assert "status" in run_output.get("C_skip", {})
        assert run_output["C_skip"]["status"] == "skipped"
        assert run_output["C_skip"]["reason"] == "Upstream failure of node B_fail."