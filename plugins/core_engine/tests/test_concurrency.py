# plugins/core_engine/tests/test_concurrency.py
import pytest
from typing import Tuple

# --- 核心导入变更 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio

class TestEngineConcurrency:
    """
    【集成测试】
    测试引擎的并发控制和原子锁机制。
    验证当多个节点并行写入共享的 'moment' 状态时，宏级原子锁能保证操作的正确性。
    """

    async def test_concurrent_writes_are_atomic(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        concurrent_write_collection: GraphCollection
    ):
        """
        测试：两个并行的节点，每个都对同一个 moment 变量进行多次增量操作，
        验证最终结果是否正确（即没有发生数据竞争）。
        """
        engine, container, _ = test_engine_setup
        
        # 1. Arrange: 创建沙盒，并在 'initial_moment' 中初始化共享计数器。
        sandbox = await sandbox_factory(
            graph_collection=concurrent_write_collection,
            initial_moment={"counter": 0}
        )
        
        # 2. Act: 执行一步。
        updated_sandbox = await engine.step(sandbox, {})
        
        # 3. Assert: 遵循新的断言模式。
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (State): 'moment' 作用域中的最终状态值是否正确。
        # 两个并行节点，每个循环100次，总共应为 200。
        expected_final_count = 200
        assert final_snapshot.moment.get("counter") == expected_final_count
        
        # Assert (Output): 依赖于最终状态的节点的输出是否正确。
        assert final_snapshot.run_output["reader"]["output"] == expected_final_count

    async def test_map_handles_concurrent_world_writes(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_concurrent_write: GraphCollection
    ):
        """
        测试：system.flow.map 并行执行多个子图，
        每个子图都修改同一个 moment 变量，验证最终结果的原子性。
        """
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = await sandbox_factory(
            graph_collection=map_collection_concurrent_write,
            initial_moment={"gold": 0}
        )

        # Act
        updated_sandbox = await engine.step(sandbox, {})

        # Assert
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # 10个并行的子图，每个增加 10 gold，总共应为 100。
        expected_gold = 100 
        assert final_snapshot.moment.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold

    async def test_codex_handles_concurrent_world_writes(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        codex_sandbox_factory: callable, # 使用为 Codex 定制的工厂
        codex_concurrent_world_write_data: dict
    ):
        """
        测试：当 codex.invoke 激活多个并行条目，且每个条目的宏都修改
        同一个 moment 变量时，结果是否正确。
        """
        engine, container, _ = test_engine_setup
        
        # Arrange: 使用 codex_sandbox_factory 处理复杂的 fixture 数据。
        sandbox = await codex_sandbox_factory(
            codex_data=codex_concurrent_world_write_data,
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})

        # Assert
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # codex 的三个条目都会被激活，它们的宏会原子性地执行。
        # 初始值为 0，期望结果为 0 + 1 + 2 + 3 = 6。
        expected_count = 6
        assert final_snapshot.moment.get("counter") == expected_count
        assert final_snapshot.run_output["reader"]["output"] == expected_count