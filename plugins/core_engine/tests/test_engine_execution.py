import pytest
from typing import Tuple

# --- 【新】导入 Sandbox 模型 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行、错误处理等。"""

    async def test_linear_flow(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
        sandbox_factory: callable,
        linear_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # 1. Arrange: 使用工厂创建沙盒
        sandbox = sandbox_factory(graph_collection=linear_collection)

        # 2. Act: 使用新的 engine.step 签名
        updated_sandbox = await engine.step(sandbox, {})
        
        # 3. Assert: 从容器获取最新的快照进行断言
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        assert "C" in output and "llm_output" in output["C"]
        assert "The story is: a story about a cat" in output["B"]["llm_output"]

    async def test_parallel_flow(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        parallel_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=parallel_collection)

        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        assert final_snapshot.run_output["merger"]["output"] == "Merged: Value A and Value B"

    async def test_pipeline_within_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        pipeline_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中设置初始状态
        sandbox = sandbox_factory(
            graph_collection=pipeline_collection,
            initial_moment={"main_character": "Initial Character"} # 可以在这里设初始值
        )

        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        # Assert: 状态被正确修改
        assert final_snapshot.moment["main_character"] == "Sir Reginald"
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        assert expected_prompt in final_snapshot.run_output["A"]["llm_output"]
        
    async def test_handles_failure_and_skips_downstream(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        failing_node_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = sandbox_factory(graph_collection=failing_node_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        assert "error" in output["B_fail"]
        assert "status" in output["C_skip"] and output["C_skip"]["status"] == "skipped"
        # 验证独立节点不受影响
        assert output["D_independent"]["output"] == "independent"

@pytest.mark.asyncio
class TestEngineStateManagement:
    """测试与状态管理（世界状态、图演化）相关的引擎功能。"""

    async def test_moment_state_persists(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        world_vars_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中设置初始状态
        sandbox = sandbox_factory(
            graph_collection=world_vars_collection,
            initial_moment={"theme": "fantasy"}
        )

        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert: 检查 moment 作用域
        assert final_snapshot.moment.get("theme") == "cyberpunk"
        assert final_snapshot.run_output["reader"]["output"] == "The theme is: cyberpunk"

    async def test_graph_evolution(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        graph_evolution_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = sandbox_factory(graph_collection=graph_evolution_collection)

        # Act: 第一步，执行图演化
        sandbox_after_evolution = await engine.step(sandbox, {})
        
        # Assert 1: 检查 lore 是否被正确修改
        new_graph_def = GraphCollection.model_validate(sandbox_after_evolution.lore["graphs"])
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        # Act 2: 第二步，使用演化后的沙盒再次执行
        final_updated_sandbox = await engine.step(sandbox_after_evolution, {})
        final_snapshot = container.resolve("snapshot_store").get(final_updated_sandbox.head_snapshot_id)

        # Assert 2: 确认新图被正确执行
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"