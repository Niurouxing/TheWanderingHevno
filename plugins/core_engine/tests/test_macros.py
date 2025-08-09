# plugins/core_engine/tests/test_macros.py

import pytest
from typing import Tuple

# --- 核心导入 ---
from plugins.core_engine.contracts import GraphCollection, ExecutionEngineInterface, Sandbox
from backend.core.contracts import Container, HookManager
from .robot_fixture import Robot

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

    async def test_can_store_and_use_custom_class_instances(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        custom_object_storage_collection: GraphCollection
    ):
        """
        【关键测试】验证自定义类的实例可以被创建、存储在 moment 中、
        在后续节点中被加载、其方法被调用，并且状态更改被持久化。
        """
        engine, container, _ = test_engine_setup
        
        # 1. Arrange
        sandbox = await sandbox_factory(
            graph_collection=custom_object_storage_collection,
            initial_moment={}
        )

        # 2. Act
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # 3. Assert
        # 3.1 验证节点的输出
        # 'use_robot' 节点的输出应该是调用 take_damage 后的 hp
        assert final_snapshot.run_output["use_robot"]["output"] == 75

        # 3.2 验证最终 moment 状态中的对象是否被正确更新
        # final_snapshot.moment 是一个纯字典，我们需要检查其中的 Robot 对象
        final_robots = final_snapshot.moment.get("robots")
        assert final_robots is not None and len(final_robots) == 2
        
        # 检查 R2-D2 的状态
        r2_final_state = final_robots[0]
        assert isinstance(r2_final_state, Robot) # 确认它被成功 unpickle
        assert r2_final_state.name == 'R2-D2'
        assert r2_final_state.hp == 75
        assert "Took 25 damage" in r2_final_state.log[0]
        
        # 检查 C-3PO 的状态 (未受影响)
        c3po_final_state = final_robots[1]
        assert isinstance(c3po_final_state, Robot)
        assert c3po_final_state.hp == 100

    async def test_can_store_and_use_dynamically_defined_class(
        self,
        test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager],
        sandbox_factory: callable,
        dynamic_class_collection: GraphCollection
    ):
        engine, container, _ = test_engine_setup
        sandbox = await sandbox_factory(graph_collection=dynamic_class_collection)
        updated_sandbox = await engine.step(sandbox, {})
        snapshot_store = container.resolve("snapshot_store")
        final_snapshot = snapshot_store.get(updated_sandbox.head_snapshot_id)

        # 节点输出是更新后的 hp
        assert final_snapshot.run_output["use_robot"]["output"] == 70
        
        # 状态中的 robot 实例也被更新了
        final_robot = final_snapshot.moment["robot_instance"]
        assert final_robot.name == "R2-D2"
        assert final_robot.hp == 70