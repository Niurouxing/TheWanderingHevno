# plugins/core_codex/tests/test_codex_runtime.py

import pytest
from uuid import uuid4
from typing import Tuple

# 从依赖插件的契约中导入数据模型和接口
from plugins.core_engine.contracts import StateSnapshot, GraphCollection, ExecutionEngineInterface
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestCodexSystem:
    """对 Hevno Codex 系统的集成测试 (codex.invoke 运行时)。"""


    async def test_basic_invoke_always_on(
        self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], codex_basic_data: dict
    ):
        engine, _, _ = test_engine
        graph = GraphCollection.model_validate(codex_basic_data["graph"])
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph,
            world_state={"codices": codex_basic_data["codices"]}
        )
        final_snapshot = await engine.step(snapshot, {})
        invoke_output = final_snapshot.run_output["invoke_test"]["output"]
        expected_text = "你好，冒险者！\n\n欢迎来到这个奇幻的世界。"
        assert invoke_output == expected_text


    @pytest.mark.asyncio
    async def test_invoke_recursion_enabled(
        self, test_engine: Tuple[ExecutionEngineInterface, Container, HookManager], codex_recursion_data: dict
    ):
        engine, _, _ = test_engine
        graph = GraphCollection.model_validate(codex_recursion_data["graph"])
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=graph,
            world_state={"codices": codex_recursion_data["codices"]}
        )
        final_snapshot = await engine.step(snapshot, {})
        invoke_result = final_snapshot.run_output["recursive_invoke"]["output"]
        final_text = invoke_result["final_text"]
        
        # 【最终修正】现在引擎行为已修复，断言应该匹配最终按优先级排序的完整结果
        # 优先级顺序: C(30), B(20), A(10), D(5)
        expected_output_string = (
            "C被B触发了，这是最终信息。\n\n"
            "B被A触发了，它又引出C。\n\n"
            "这是关于A的信息，它引出B。\n\n"
            "这是一个总是存在的背景信息。"
        )
        
        assert final_text == expected_output_string