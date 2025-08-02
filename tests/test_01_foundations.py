# tests/test_01_foundations.py
import pytest
from pydantic import ValidationError
from uuid import uuid4

from backend.models import GraphCollection, GenericNode, GraphDefinition, RuntimeInstruction
from backend.core.state import StateSnapshot, Sandbox, SnapshotStore
from backend.core.dependency_parser import build_dependency_graph


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


class TestDependencyParser:
    """测试依赖解析器，使用新的节点结构。"""

    def test_simple_dependency(self):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"config": {"value": "{{ nodes.A.output }}"}}]}]
        deps = build_dependency_graph(nodes)
        assert deps["B"] == {"A"}

    def test_dependency_in_nested_structure(self):
        nodes = [
            {"id": "source", "run": []},
            {"id": "consumer", "run": [{"config": {"nested": ["{{ nodes.source.val }}"]}}]}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["consumer"] == {"source"}

    def test_ignores_non_node_macros(self):
        nodes = [{"id": "A", "run": [{"config": {"value": "{{ world.x }}"}}]}]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()

    def test_dependency_on_placeholder_node_is_preserved(self):
        """
        验证对图中不存在的节点（即子图的输入占位符）的依赖会被保留。
        这对于 system.call 功能至关重要。
        """
        nodes = [{"id": "A", "run": [{"config": {"value": "{{ nodes.placeholder_input.val }}"}}]}]
        deps = build_dependency_graph(nodes)
        # 之前这里断言 deps["A"] == set()，现在它必须保留依赖
        assert deps["A"] == {"placeholder_input"}