# plugins/core_engine/tests/test_engine_execution.py

import pytest
from typing import Tuple

# --- 核心导入变更 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
class TestEngineCoreFlows:
    """
    【集成测试】
    测试引擎的核心执行流程，如线性、并行、错误处理等。
    这些测试不关心状态的持久化细节，只关心图的逻辑是否按预期执行。
    """

    async def test_linear_flow(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
        sandbox_factory: callable,
        linear_collection: GraphCollection
    ):
        """测试一个简单的线性依赖图 (A -> B -> C) 是否能正确执行。"""
        engine, container, _ = test_engine_setup
        
        # 1. Arrange: 使用工厂创建沙盒，提供图定义。
        sandbox = await sandbox_factory(graph_collection=linear_collection)

        # 2. Act: 使用 engine.step 执行一步计算。
        updated_sandbox = await engine.step(sandbox, {})
        
        # 3. Assert: 遵循新的断言模式获取最终快照。
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # 从最终快照的 run_output 中验证节点结果。
        output = final_snapshot.run_output
        assert "C" in output and "llm_output" in output["C"]
        assert "The story is: a story about a cat" in output["B"]["llm_output"]

    async def test_parallel_flow(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        parallel_collection: GraphCollection
    ):
        """测试两个无依赖的并行节点是否能被一个下游节点正确消费。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=parallel_collection)

        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        assert final_snapshot.run_output["merger"]["output"] == "Merged: Value A and Value B"

    async def test_pipeline_within_node(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        pipeline_collection: GraphCollection
    ):
        """测试单个节点内的指令管道 (`pipe` 对象) 和对 `moment` 状态的修改。"""
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中设置初始状态。
        sandbox = await sandbox_factory(
            graph_collection=pipeline_collection,
            initial_moment={"main_character": "Initial Character"}
        )

        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # Assert (State): 验证 moment 状态被节点内的第一个指令正确修改。
        assert final_snapshot.moment["main_character"] == "Sir Reginald"
        
        # Assert (Output): 验证节点内的第二个指令正确地消费了第三个指令的输入 (`pipe` 对象)。
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        assert expected_prompt in final_snapshot.run_output["A"]["llm_output"]
        
    async def test_handles_failure_and_skips_downstream(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        failing_node_collection: GraphCollection
    ):
        """测试当一个节点失败时，其下游依赖节点会被跳过，而并行节点不受影响。"""
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=failing_node_collection)
        
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        output = final_snapshot.run_output
        # 验证失败的节点返回了错误信息
        assert "error" in output["B_fail"]
        # 验证下游节点被标记为 skipped
        assert "status" in output["C_skip"] and output["C_skip"]["status"] == "skipped"
        # 验证独立的并行节点成功执行
        assert output["D_independent"]["output"] == "independent"


@pytest.mark.asyncio
class TestEngineStateManagement:
    """
    【关键集成测试】
    测试与新的三层状态管理（世界状态、图演化）相关的引擎功能。
    """

    async def test_moment_state_persists_across_nodes(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        world_vars_collection: GraphCollection
    ):
        """测试一个节点对 `moment` 的修改能被后续节点读取到。"""
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中设置初始状态。
        sandbox = await sandbox_factory(
            graph_collection=world_vars_collection,
            initial_moment={"theme": "fantasy"}
        )

        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (State): 检查最终的 moment 作用域。
        assert final_snapshot.moment.get("theme") == "cyberpunk"
        # Assert (Output): 检查读取状态的节点是否获得了正确的值。
        assert final_snapshot.run_output["reader"]["output"] == "The theme is: cyberpunk"

    async def test_graph_evolution_by_modifying_lore(
        self, 
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        graph_evolution_collection: GraphCollection
    ):
        """
        测试图的自我演化：
        1. 执行一个修改 `lore.graphs` 的图。
        2. 验证返回的沙盒中 `lore` 已被更新。
        3. 使用更新后的沙盒再次执行，验证新图被执行。
        """
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = await sandbox_factory(graph_collection=graph_evolution_collection)

        # Act 1: 第一次执行，进行图演化。
        sandbox_after_evolution = await engine.step(sandbox, {})
        
        # Assert 1 (State): 检查返回的沙盒对象中，lore.graphs 是否被正确修改。
        new_graph_def = GraphCollection.model_validate(sandbox_after_evolution.lore["graphs"])
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        # Act 2: 第二次执行，使用已演化后的沙盒。
        final_updated_sandbox = await engine.step(sandbox_after_evolution, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(final_updated_sandbox.head_snapshot_id)

        # Assert 2 (Output): 确认新图被正确执行。
        assert "new_node" in final_snapshot.run_output
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"