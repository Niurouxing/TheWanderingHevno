# plugins/core_engine/tests/test_concurrency.py
import pytest
from typing import Tuple

# --- 【新】导入 Sandbox 和 GraphCollection ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineConcurrency:
    """测试引擎的并发控制和原子锁机制。"""

    async def test_concurrent_writes_are_atomic(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        concurrent_write_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 在 initial_moment 中初始化计数器
        sandbox = sandbox_factory(
            graph_collection=concurrent_write_collection,
            initial_moment={"counter": 0}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert: 检查 moment 作用域中的最终计数值
        expected_final_count = 200
        assert final_snapshot.moment.get("counter") == expected_final_count
        assert final_snapshot.run_output["reader"]["output"] == expected_final_count

    async def test_map_handles_concurrent_world_writes(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        map_collection_concurrent_write: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = sandbox_factory(
            graph_collection=map_collection_concurrent_write,
            initial_moment={"gold": 0}
        )

        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert
        expected_gold = 100 # 10 tasks * 10 gold
        assert final_snapshot.moment.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold

    async def test_codex_handles_concurrent_world_writes(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        codex_concurrent_world_write_data: dict
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 使用解包语法从 fixture 中设置 lore 和 moment
        # codex_concurrent_world_write_data 的结构是 {"lore": {...}, "moment": {...}}
        # 我们需要从 lore 中提取图定义
        graph_collection = GraphCollection.model_validate(codex_concurrent_world_write_data["lore"]["graphs"])
        
        sandbox = sandbox_factory(
            graph_collection=graph_collection,
            initial_lore=codex_concurrent_world_write_data["lore"],
            initial_moment=codex_concurrent_world_write_data["moment"]
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)

        # Assert
        # The codex entries are executed in priority order (30, 20, 10), but their macros are atomic.
        # Expected: 0 + 3 + 2 + 1 = 6
        expected_count = 6
        assert final_snapshot.moment.get("counter") == expected_count
        assert final_snapshot.run_output["reader"]["output"] == expected_count