# plugins/core_engine/tests/test_macros.py

import pytest
from typing import Tuple

# --- 核心导入 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
class TestAdvancedMacrosAndRuntimes:
    """
    【集成测试】
    测试高级宏功能和 `system.*` 运行时的集成。
    """

    async def test_advanced_macros_with_dynamic_functions_and_state_changes(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        advanced_macro_collection: GraphCollection
    ):
        """
        测试：
        1. 在宏中动态定义函数并附加到 `moment` 对象上。
        2. 后续节点能成功调用这个动态定义的函数。
        3. 宏能正确修改 `moment` 状态。
        """
        engine, container, _ = test_engine_setup
        
        # Arrange: 将初始状态放入 moment。
        sandbox = await sandbox_factory(
            graph_collection=advanced_macro_collection,
            initial_moment={"game_difficulty": "easy"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (State): moment 状态被后续的宏正确修改。
        assert final_snapshot.moment["game_difficulty"] == "hard"
        
        # Assert (Output): 动态定义的函数被正确调用。
        assert final_snapshot.run_output["use_skill"]["output"] == 5.0

    async def test_execute_runtime_for_double_evaluation(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        execute_runtime_collection: GraphCollection
    ):
        """测试 `system.execute` 运行时能否对一个字符串进行二次求值并执行。"""
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = await sandbox_factory(
            graph_collection=execute_runtime_collection,
            initial_moment={"player_status": "normal"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (State): 验证二次求值成功修改了 moment 状态。
        assert final_snapshot.moment["player_status"] == "empowered"

    async def test_data_format_runtime(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        """测试 `system.data.format` 运行时能否正确格式化列表数据。"""
        engine, container, _ = test_engine_setup
        
        # Arrange: 将图定义直接内联，以保持测试的独立性和清晰性。
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "data", "run": [{"runtime": "system.io.input", "config": {"value": [{"name": "A"}, {"name": "B"}]}}]},
            {"id": "formatter", "run": [{"runtime": "system.data.format", "config": {
                "items": "{{ nodes.data.output }}",
                "template": "- {item[name]}",
                "joiner": ", "
            }}]}
        ]}})
        sandbox = await sandbox_factory(graph_collection=graph)
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        assert final_snapshot.run_output["formatter"]["output"] == "- A, - B"

    async def test_data_parse_runtime(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        """测试 `system.data.parse` 运行时能否正确解析 JSON 字符串。"""
        engine, container, _ = test_engine_setup
        
        # Arrange
        llm_output = '{"result": "success", "value": 42}'
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "parser", "run": [{"runtime": "system.data.parse", "config": {
                "text": llm_output,
                "format": "json"
            }}]}
        ]}})
        sandbox = await sandbox_factory(graph_collection=graph)
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        parsed_output = final_snapshot.run_output["parser"]["output"]
        assert parsed_output == {"result": "success", "value": 42}

    async def test_data_regex_runtime_with_named_groups(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        """测试 `system.data.regex` 运行时能否使用命名捕获组提取数据。"""
        engine, container, _ = test_engine_setup
        
        # Arrange
        text = "Action: ATTACK, Target: GOBLIN"
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "matcher", "run": [{"runtime": "system.data.regex", "config": {
                "text": text,
                "pattern": r"Action: (?P<action>\w+), Target: (?P<target>\w+)",
                "mode": "search"
            }}]}
        ]}})
        sandbox = await sandbox_factory(graph_collection=graph)
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)
        
        # Assert (Output)
        regex_output = final_snapshot.run_output["matcher"]["output"]
        assert regex_output == {"action": "ATTACK", "target": "GOBLIN"}