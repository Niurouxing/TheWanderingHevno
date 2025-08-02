# plugins/core_codex/tests/test_codex_runtime.py

import pytest
from uuid import uuid4

from backend.core.contracts import StateSnapshot, GraphCollection
from backend.core.contracts import ExecutionEngineInterface

@pytest.mark.asyncio
class TestCodexSystem:
    """对 Hevno Codex 系统的集成测试 (system.invoke 运行时)。"""


    async def test_basic_invoke_always_on(
        self, test_engine: ExecutionEngineInterface, codex_basic_data: dict
    ):
        graph = GraphCollection.model_validate(codex_basic_data["graph"])
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph,
            world_state={"codices": codex_basic_data["codices"]}
        )
        final_snapshot = await test_engine.step(snapshot, {})
        invoke_output = final_snapshot.run_output["invoke_test"]["output"]
        expected_text = "你好，冒险者！\n\n欢迎来到这个奇幻的世界。"
        assert invoke_output == expected_text


    async def test_invoke_recursion_enabled(
        self, test_engine: ExecutionEngineInterface, codex_recursion_data: dict
    ):
        graph = GraphCollection.model_validate(codex_recursion_data["graph"])
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph,
            world_state={"codices": codex_recursion_data["codices"]}
        )
        final_snapshot = await test_engine.step(snapshot, {})
        invoke_result = final_snapshot.run_output["recursive_invoke"]["output"]
        final_text = invoke_result["final_text"]
        expected_rendered_order = [
            "这是关于A的信息，它引出B。",
            "B被A触发了，它又引出C。",
            "C被B触发了，这是最终信息。",
            "这是一个总是存在的背景信息。",
        ]
        assert final_text.split("\n\n") == expected_rendered_order