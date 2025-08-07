# plugins/core_codex/tests/test_codex_runtime.py 

import pytest
from uuid import uuid4
from typing import Tuple

# 导入新的测试依赖
from plugins.core_engine.contracts import Sandbox, ExecutionEngineInterface, GraphCollection 
from backend.core.contracts import Container, HookManager

# 标记所有测试为异步
pytestmark = pytest.mark.asyncio

@pytest.fixture
def codex_sandbox_factory(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
    sandbox_factory: callable
) -> callable:
    """
    一个便利的包装器，将通用的 sandbox_factory 和 codex 测试数据结合起来。
    """
    def _create_codex_sandbox(codex_data: dict) -> Sandbox:
        # 从 codex_data 中分离出图、lore 和 moment
        graph_collection_dict = codex_data.get("lore", {}).get("graphs", {})
        initial_lore = codex_data.get("lore", {})
        initial_moment = codex_data.get("moment", {})
        
        # 从 lore 数据中移除 'graphs'，因为它会被自动添加
        if 'graphs' in initial_lore:
            del initial_lore['graphs']
            
        # --- 【修复】核心变更点 ---
        # 1. 将图的字典验证为 Pydantic 模型实例
        graph_collection_obj = GraphCollection.model_validate(graph_collection_dict)

        # 2. 调用父工厂，并使用正确的关键字参数名 `graph_collection`
        return sandbox_factory(
            graph_collection=graph_collection_obj, # <-- 使用正确的参数名和对象
            initial_lore=initial_lore,
            initial_moment=initial_moment
        )
        # ------------------------

    return _create_codex_sandbox


async def test_basic_invoke_always_on(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager], 
    codex_sandbox_factory: callable,
    codex_basic_data: dict
):
    """测试 'always_on' 模式和优先级排序。"""
    engine, container, _ = test_engine_setup
    
    # 【修复】从测试数据中提取图，因为 codex_sandbox_factory 不再处理它
    codex_basic_data["lore"]["graphs"] = {"main": {"nodes": [{"id": "invoke_test", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "info"}]}}]}]}}
    sandbox = codex_sandbox_factory(codex_basic_data)
    
    final_sandbox = await engine.step(sandbox, {})

    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    
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
    
    # 【修复】从测试数据中提取图
    codex_recursion_data["lore"]["graphs"] = {"main": {"nodes": [{"id": "recursive_invoke", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "lore", "source": "A"}], "recursion_enabled": True, "debug": True}}]}]}}
    sandbox = codex_sandbox_factory(codex_recursion_data)

    final_sandbox = await engine.step(sandbox, {})

    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    
    invoke_result = final_snapshot.run_output["recursive_invoke"]["output"]
    final_text = invoke_result["final_text"]
    
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
    【全新的关键测试】
    验证 codex.invoke 是否能正确地从 lore 和 moment 中合并知识，
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
                    # 这个条目将覆盖 Lore 中的同名、同优先级的条目
                    {"id": "base_rule", "content": "临时规则：由于天气炎热，火球术造成15点伤害。", "priority": 10},
                    # 这个条目是 Moment 独有的
                    {"id": "moment_specific", "content": "这是一个仅在当前时刻有效的规则。", "priority": 20}
                ]}
            }
        }
    }
    sandbox = codex_sandbox_factory(codex_data)

    # Act
    final_sandbox = await engine.step(sandbox, {})

    # Assert
    snapshot_store = container.resolve("snapshot_store")
    final_snapshot = snapshot_store.get(final_sandbox.head_snapshot_id)
    invoke_output = final_snapshot.run_output["invoke"]["output"]
    
    # 期望输出按优先级排序：moment_specific(20), base_rule(10 from moment), lore_specific(5)
    expected_text = (
        "这是一个仅在当前时刻有效的规则。\n\n"
        "临时规则：由于天气炎热，火球术造成15点伤害。\n\n"
        "这是一个仅存在于Lore的规则。"
    )
    assert invoke_output == expected_text