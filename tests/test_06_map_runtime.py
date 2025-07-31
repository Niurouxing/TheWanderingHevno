# tests/test_06_map_runtime.py

import pytest
from uuid import uuid4

from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

@pytest.mark.asyncio
class TestEngineMapExecution:
    """
    对 system.map 运行时的集成测试。
    """

    async def test_basic_map_execution(
        self,
        test_engine: ExecutionEngine,
        map_collection_basic: GraphCollection
    ):
        """
        测试基本的 scatter-gather 功能，不使用 collect。
        期望输出是每个子图执行结果的完整字典的列表。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_basic
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        map_result = output["character_processor_map"]["output"]

        # 1. 验证输出是一个包含3个元素的列表
        assert isinstance(map_result, list)
        assert len(map_result) == 3

        # 2. 验证每个元素都是一个子图的完整结果字典
        assert "generate_bio" in map_result[0]
        assert "generate_bio" in map_result[1]
        assert "generate_bio" in map_result[2]

        # 3. 详细验证第一个子图的输出，确保 source.item, source.index 和外部节点引用都正确
        first_bio_prompt = map_result[0]["generate_bio"]["llm_output"]
        expected_prompt = "LLM_RESPONSE_FOR:[Create a bio for Aragorn in the context of The Fellowship of the Ring. Index: 0]"
        assert first_bio_prompt == expected_prompt
        
        # 4. 验证最后一个子图的输出
        last_bio_prompt = map_result[2]["generate_bio"]["llm_output"]
        expected_prompt_last = "LLM_RESPONSE_FOR:[Create a bio for Legolas in the context of The Fellowship of the Ring. Index: 2]"
        assert last_bio_prompt == expected_prompt_last

    async def test_map_with_collect(
        self,
        test_engine: ExecutionEngine,
        map_collection_with_collect: GraphCollection
    ):
        """
        测试 `collect` 功能，期望输出是一个扁平化的值列表。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_with_collect
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # --- 【核心修正】---
        # 恢复被意外删除的行
        output = final_snapshot.run_output
        map_result = output["character_processor_map"]["output"]

        # 1. 验证输出是一个扁平列表
        assert isinstance(map_result, list)
        assert len(map_result) == 3

        # 2. 验证列表中的每个元素都是从子图提取的 `summary` 字符串
        # 使用我们之前修正过的正确字符串
        assert map_result[0] == "Summary of 'Create a bio for Ara...'"
        assert map_result[1] == "Summary of 'Create a bio for Gan...'"
        assert map_result[2] == "Summary of 'Create a bio for Leg...'"

    async def test_map_handles_concurrent_world_writes(
        self,
        test_engine: ExecutionEngine,
        map_collection_concurrent_write: GraphCollection
    ):
        """
        验证在 map 中并发写入 world_state 是原子和安全的。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_concurrent_write,
            world_state={"gold": 0} # 初始金币为0
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 10个并行任务，每个增加10金币
        expected_gold = 100

        # 1. 验证最终的 world_state
        assert final_snapshot.world_state.get("gold") == expected_gold
        
        # 2. 验证 reader 节点读取到的值
        output = final_snapshot.run_output
        reader_output = output["reader"]["output"]
        assert reader_output == expected_gold

    async def test_map_handles_partial_failures_gracefully(
        self,
        test_engine: ExecutionEngine,
        map_collection_with_failure: GraphCollection
    ):
        """
        测试当 map 迭代中的某些子图失败时，整体操作不会崩溃，
        并且返回的结果中能清晰地标识出成功和失败的项。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=map_collection_with_failure
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        map_result = output["mapper"]["output"]

        # 1. 验证结果列表长度仍然是3
        assert len(map_result) == 3

        # 2. 验证成功的项
        # 第一个子图 (Alice)
        assert "error" not in map_result[0].get("get_name", {})
        assert map_result[0]["get_name"]["output"] == "Alice"
        # 第三个子图 (Charlie)
        assert "error" not in map_result[2].get("get_name", {})
        assert map_result[2]["get_name"]["output"] == "Charlie"

        # 3. 验证失败的项
        # 第二个子图 (Bob)
        failed_item_result = map_result[1]
        assert "get_name" in failed_item_result
        assert "error" in failed_item_result["get_name"]
        # 错误应该是因为对 str 对象调用 .name
        assert "AttributeError" in failed_item_result["get_name"]["error"]