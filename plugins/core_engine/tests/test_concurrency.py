# plugins/core_engine/tests/test_concurrency.py

import pytest
from uuid import uuid4
from typing import Tuple

# 从本插件的契约中导入数据模型和接口
from plugins.core_engine.contracts import StateSnapshot, GraphCollection, ExecutionEngineInterface
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestEngineConcurrency:
    """测试引擎的并发控制和原子锁机制。"""

    async def test_concurrent_writes_are_atomic(
        self, 
        test_engine: Tuple[ExecutionEngineInterface, Container, HookManager],
        concurrent_write_collection: GraphCollection
    ):
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

    async def test_map_handles_concurrent_world_writes(
        self,
        test_engine: Tuple[ExecutionEngineInterface, Container, HookManager],
        map_collection_concurrent_write: GraphCollection
    ):
        engine, _, _ = test_engine
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0}
        )
        final_snapshot = await engine.step(initial_snapshot, {})
        
        expected_gold = 100
        assert final_snapshot.world_state.get("gold") == expected_gold
        assert final_snapshot.run_output["reader"]["output"] == expected_gold