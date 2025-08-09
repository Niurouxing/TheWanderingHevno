# plugins/core_codex/tests/test_codex_runtime.py 

import pytest
from typing import Tuple

from plugins.core_engine.contracts import Sandbox, ExecutionEngineInterface, GraphCollection
from backend.core.contracts import Container, HookManager

# 标记所有测试为异步
pytestmark = pytest.mark.asyncio

@pytest.fixture
def codex_sandbox_factory(
    sandbox_factory: callable
) -> callable:
    """
    一个便利的包装器，将通用的 sandbox_factory 和 codex 测试数据结合起来。
    """
    async def _create_codex_sandbox(codex_data: dict) -> Sandbox:
        graph_collection_dict = codex_data.get("lore", {}).get("graphs", {})
        initial_lore = codex_data.get("lore", {})
        initial_moment = codex_data.get("moment", {})
        
        if 'graphs' in initial_lore:
            del initial_lore['graphs']
            
        graph_collection_obj = GraphCollection.model_validate(graph_collection_dict)

        return await sandbox_factory(
            graph_collection=graph_collection_obj,
            initial_lore=initial_lore,
            initial_moment=initial_moment
        )

    return _create_codex_sandbox


async def test_basic_invoke_always_on(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
    codex_sandbox_factory: callable,
    codex_basic_data: dict
):
    """测试 'always_on' 模式和优先级排序。"""
    engine, container, _ = test_engine_setup
    sandbox = await codex_sandbox_factory(codex_basic_data)
    
    final_sandbox = await engine.step(sandbox, {})

    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    invoke_output = final_snapshot.run_output["invoke_test"]["output"]
    expected_text = "你好，冒险者！\n\n欢迎来到这个奇幻的世界。"
    assert invoke_output == expected_text

async def test_invoke_recursion_enabled(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
    codex_sandbox_factory: callable,
    codex_recursion_data: dict
):
    """测试递归激活功能。"""
    engine, container, _ = test_engine_setup
    
    # 移除 debug 模式，因为默认的输出就是我们需要的文本
    codex_recursion_data["lore"]["graphs"]["main"]["nodes"][0]["run"][0]["config"]["debug"] = False
    sandbox = await codex_sandbox_factory(codex_recursion_data)

    final_sandbox = await engine.step(sandbox, {})

    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None
    
    # 【修复】从 final_snapshot.run_output 获取结果，而不是 final_sandbox
    final_text = final_snapshot.run_output["recursive_invoke"]["output"]
    
    expected_output_string = (
        "C被B触发了，这是最终信息。\n\n"
        "B被A触发了，它又引出C。\n\n"
        "这是关于A的信息，它引出B。\n\n"
        "这是一个总是存在的背景信息。"
    )
    assert final_text == expected_output_string

async def test_codex_reads_from_lore_and_moment(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    codex_sandbox_factory: callable
):
    """
    【关键测试】验证 codex.invoke 能正确地从 lore 和 moment 中合并知识，
    并遵循 moment 覆盖 lore 的规则。
    """
    engine, container, _ = test_engine_setup

    # Arrange
    codex_data = {
        "lore": {
            "graphs": {"main": {"nodes": [{"id": "invoke", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "rules"}]}}]}]}},
            "codices": {
                "rules": {"entries": [
                    {"id": "base_rule", "content": "基础规则：火球术造成10点伤害。", "priority": 10},
                    {"id": "lore_specific", "content": "这是一个仅存在于Lore的规则。", "priority": 5}
                ]}
            }
        },
        "moment": {
            "codices": {
                "rules": {"entries": [
                    {"id": "base_rule", "content": "临时规则：由于天气炎热，火球术造成15点伤害。", "priority": 10},
                    {"id": "moment_specific", "content": "这是一个仅在当前时刻有效的规则。", "priority": 20}
                ]}
            }
        }
    }
    sandbox = await codex_sandbox_factory(codex_data)

    # Act
    final_sandbox = await engine.step(sandbox, {})

    # Assert
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    assert final_snapshot is not None

    invoke_output = final_snapshot.run_output["invoke"]["output"]
    
    expected_text = (
        "这是一个仅在当前时刻有效的规则。\n\n"
        "临时规则：由于天气炎热，火球术造成15点伤害。\n\n"
        "这是一个仅存在于Lore的规则。"
    )
    assert invoke_output == expected_text