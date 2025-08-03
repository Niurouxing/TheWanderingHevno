# plugins/core_engine/tests/test_concurrency.py
import pytest
from uuid import uuid4
from typing import Tuple

from plugins.core_engine.contracts import StateSnapshot, GraphCollection, ExecutionEngineInterface
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineConcurrency:
    """测试引擎的并发控制和原子锁机制。"""

    async def test_concurrent_writes_are_atomic(self, test_engine, concurrent_write_collection):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=concurrent_write_collection,
            world_state={"counter": 0}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        
        expected_final_count = 200
        assert final_snapshot.world_state.get("counter") == expected_final_count
        assert final_snapshot.run_output["reader"]["output"] == expected_final_count

    async def test_map_handles_concurrent_world_writes(self, test_engine, map_collection_concurrent_write):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        
        expected_gold = 100 # 10 tasks * 10 gold
        assert final_snapshot.world_state.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold

    async def test_codex_handles_concurrent_world_writes(self, test_engine, codex_concurrent_world_write_data):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=GraphCollection.model_validate(codex_concurrent_world_write_data["graph"]),
            world_state={"counter": 0, "codices": codex_concurrent_world_write_data["codices"]}
        )
        final_snapshot = await engine.step(initial_snapshot, {})

        # The codex entries are executed in priority order (30, 20, 10), but their macros are atomic.
        # Expected: 0 + 3 + 2 + 1 = 6
        expected_count = 6
        assert final_snapshot.world_state.get("counter") == expected_count
        assert final_snapshot.run_output["reader"]["output"] == expected_count