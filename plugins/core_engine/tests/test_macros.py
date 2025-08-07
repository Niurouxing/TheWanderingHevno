import pytest
from typing import Tuple

# --- 【新】导入 Sandbox 模型 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager

@pytest.mark.asyncio
class TestAdvancedMacrosAndRuntimes:

    async def test_advanced_macros_with_depends_on(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        advanced_macro_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 将初始状态放入 moment
        sandbox = sandbox_factory(
            graph_collection=advanced_macro_collection,
            initial_moment={"game_difficulty": "easy"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert 1: 函数被正确定义和使用
        assert final_snapshot.run_output["use_skill"]["output"] == 5.0

        # Assert 2: moment 状态被正确修改
        assert final_snapshot.moment["game_difficulty"] == "hard"

    async def test_execute_runtime(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        execute_runtime_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange
        sandbox = sandbox_factory(
            graph_collection=execute_runtime_collection,
            initial_moment={"player_status": "normal"}
        )
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert
        assert final_snapshot.moment["player_status"] == "empowered"

    async def test_data_format_runtime(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange: 将图定义直接内联
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "data", "run": [{"runtime": "system.io.input", "config": {"value": [{"name": "A"}, {"name": "B"}]}}]},
            {"id": "formatter", "run": [{"runtime": "system.data.format", "config": {
                "items": "{{ nodes.data.output }}",
                "template": "- {item[name]}",
                "joiner": ", "
            }}]}
        ]}})
        sandbox = sandbox_factory(graph_collection=graph)
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert
        assert final_snapshot.run_output["formatter"]["output"] == "- A, - B"

    async def test_data_parse_runtime(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
        engine, container, _ = test_engine_setup
        
        # Arrange
        llm_output = '{"result": "success", "value": 42}'
        graph = GraphCollection.model_validate({"main": {"nodes": [
            {"id": "parser", "run": [{"runtime": "system.data.parse", "config": {
                "text": llm_output,
                "format": "json"
            }}]}
        ]}})
        sandbox = sandbox_factory(graph_collection=graph)
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert
        parsed_output = final_snapshot.run_output["parser"]["output"]
        assert parsed_output == {"result": "success", "value": 42}

    async def test_data_regex_runtime(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable
    ):
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
        sandbox = sandbox_factory(graph_collection=graph)
        
        # Act
        updated_sandbox = await engine.step(sandbox, {})
        final_snapshot = container.resolve("snapshot_store").get(updated_sandbox.head_snapshot_id)
        
        # Assert
        regex_output = final_snapshot.run_output["matcher"]["output"]
        assert regex_output == {"action": "ATTACK", "target": "GOBLIN"}