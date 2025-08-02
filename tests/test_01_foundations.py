# tests/test_01_foundations.py
import pytest
from pydantic import ValidationError
from uuid import uuid4

from backend.core.hooks import HookManager
from backend.core.models import GraphCollection, GenericNode, GraphDefinition, RuntimeInstruction
from backend.core.state import StateSnapshot, Sandbox, SnapshotStore
from backend.core.dependency_parser import build_dependency_graph_async


class TestCoreModels:
    """测试核心数据模型，已更新为新架构。"""

    def test_runtime_instruction_validation(self):
        """测试 RuntimeInstruction 模型。"""
        # 有效
        inst = RuntimeInstruction(runtime="test.runtime", config={"key": "value"})
        assert inst.runtime == "test.runtime"
        assert inst.config == {"key": "value"}
        # config 默认为空字典
        inst_default = RuntimeInstruction(runtime="test.runtime")
        assert inst_default.config == {}

        # 无效 (缺少 runtime)
        with pytest.raises(ValidationError):
            RuntimeInstruction(config={})

    def test_generic_node_validation_success(self):
        """测试 GenericNode 使用新的 `run` 字段。"""
        node = GenericNode(
            id="n1",
            run=[
                {"runtime": "step1", "config": {"p1": 1}},
                {"runtime": "step2"}
            ]
        )
        assert node.id == "n1"
        assert len(node.run) == 2
        assert isinstance(node.run[0], RuntimeInstruction)
        assert node.run[0].runtime == "step1"
        assert node.run[0].config == {"p1": 1}
        assert node.run[1].config == {}

    def test_generic_node_validation_fails(self):
        """测试 GenericNode 的无效 `run` 字段。"""
        # `run` 列表中的项不是有效的指令
        with pytest.raises(ValidationError):
            GenericNode(id="n1", run=["not_an_instruction"])
        
        with pytest.raises(ValidationError):
            GenericNode(id="n1", run=[{"config": {}}]) # runtime 缺失

    def test_graph_collection_validation(self):
        """测试 GraphCollection 验证逻辑，此逻辑不变。"""
        valid_data = {"main": {"nodes": [{"id": "a", "run": []}]}}
        collection = GraphCollection.model_validate(valid_data)
        assert "main" in collection.root

        with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate({"other": {"nodes": []}})


class TestSandboxModels:
    """测试沙盒相关模型，基本不变。"""
    # ... 此部分测试与旧版本基本一致，无需修改，因为模型本身的结构和不变性没有改变 ...
    @pytest.fixture
    def sample_graph_collection(self) -> GraphCollection:
        return GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "run": []}]}})

    def test_state_snapshot_is_immutable(self, sample_graph_collection: GraphCollection):
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=sample_graph_collection)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            snapshot.world_state = {"new_key": "new_value"}


@pytest.mark.asyncio # <-- 【新增】为整个测试类标记为异步
class TestDependencyParser:
    """测试依赖解析器，使用新的节点结构。"""

    # 【修改】所有测试方法现在都是 async
    async def test_simple_dependency(self, hook_manager: HookManager):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"runtime": "test", "config": {"value": "{{ nodes.A.output }}"}}]}]
        # 【修改】使用 await
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["B"] == {"A"}

    async def test_dependency_in_nested_structure(self, hook_manager: HookManager):
        nodes = [{"id": "source", "run": []}, {"id": "consumer", "run": [{"runtime": "test", "config": {"nested": ["{{ nodes.source.val }}"]}}]}]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["consumer"] == {"source"}

    async def test_ignores_non_node_macros(self, hook_manager: HookManager):
        nodes = [{"id": "A", "run": [{"runtime": "test", "config": {"value": "{{ world.x }}"}}]}]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["A"] == set()

    async def test_dependency_on_placeholder_node_is_preserved(self, hook_manager: HookManager):
        nodes = [{"id": "A", "run": [{"runtime": "test", "config": {"value": "{{ nodes.placeholder_input.val }}"}}]}]
        deps = await build_dependency_graph_async(nodes, hook_manager)
        assert deps["A"] == {"placeholder_input"}