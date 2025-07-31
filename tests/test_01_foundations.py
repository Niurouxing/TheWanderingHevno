# tests/test_01_foundations.py
import pytest
from pydantic import ValidationError
from uuid import uuid4

# ---------------------------------------------------------------------------
# 导入被测试的类
# ---------------------------------------------------------------------------
from backend.models import GraphCollection, GenericNode, GraphDefinition
from backend.core.state_models import StateSnapshot, Sandbox, SnapshotStore
from backend.core.dependency_parser import build_dependency_graph


# ---------------------------------------------------------------------------
# Section 1: Core Data Models (`models.py`)
# - 这部分测试不受影响，因为模型验证逻辑没有改变。
# ---------------------------------------------------------------------------

class TestCoreModels:
    """测试核心数据模型：GenericNode, GraphDefinition, GraphCollection"""

    def test_generic_node_validation_success(self):
        """测试 GenericNode 的有效数据格式。"""
        # 字符串 runtime
        node1 = GenericNode(id="n1", data={"runtime": "test.runtime"})
        assert node1.id == "n1"
        assert node1.data["runtime"] == "test.runtime"
        
        # 字符串列表 runtime
        node2 = GenericNode(id="n2", data={"runtime": ["step1", "step2"]})
        assert node2.data["runtime"] == ["step1", "step2"]
        
        # 宏系统下，节点甚至可以没有 runtime，作为纯数据持有者
        node3 = GenericNode(id="n3", data={"value": "{{ 1 + 1 }}"})
        assert "runtime" not in node3.data

    def test_generic_node_validation_fails(self):
        """测试 GenericNode 的无效数据格式（除了缺少runtime）。"""
        # runtime 类型错误（非字符串或字符串列表）
        with pytest.raises(ValidationError, match="'runtime' must be a string or a list of strings"):
            GenericNode(id="n2", data={"runtime": 123})
            
        with pytest.raises(ValidationError, match="'runtime' must be a string or a list of strings"):
            GenericNode(id="n3", data={"runtime": ["step1", 2]})

    def test_graph_collection_validation(self):
        """测试 GraphCollection 模型的验证逻辑。"""
        # 1. 有效数据
        valid_data = {"main": {"nodes": [{"id": "a", "data": {"runtime": "test"}}]}}
        collection = GraphCollection.model_validate(valid_data)
        assert "main" in collection.root
        assert isinstance(collection.root["main"], GraphDefinition)
        assert len(collection.root["main"].nodes) == 1

        # 2. 缺少 "main" 图应该失败
        with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate({"other_graph": {"nodes": []}})

        # 3. 节点验证失败会冒泡到顶层
        with pytest.raises(ValidationError, match="must be a string or a list of strings"):
            GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "data": {"runtime": 123}}]}})


# ---------------------------------------------------------------------------
# Section 2: Sandbox Models (`core/state_models.py`)
# - 这部分测试不受影响，因为状态管理模型没有改变。
# ---------------------------------------------------------------------------

class TestSandboxModels:
    """测试沙盒相关的数据模型：StateSnapshot, Sandbox, SnapshotStore"""

    @pytest.fixture
    def sample_graph_collection(self) -> GraphCollection:
        """提供一个简单的 GraphCollection 用于创建快照。"""
        return GraphCollection.model_validate({
            "main": {"nodes": [{"id": "a", "data": {"runtime": "test"}}]}
        })

    def test_state_snapshot_creation(self, sample_graph_collection: GraphCollection):
        """测试 StateSnapshot 的创建和默认值。"""
        sandbox_id = uuid4()
        snapshot = StateSnapshot(
            sandbox_id=sandbox_id,
            graph_collection=sample_graph_collection
        )
        assert snapshot.sandbox_id == sandbox_id
        assert snapshot.id is not None
        assert snapshot.created_at is not None
        assert snapshot.parent_snapshot_id is None
        assert snapshot.world_state == {}

    def test_state_snapshot_is_immutable(self, sample_graph_collection: GraphCollection):
        """关键测试：验证 StateSnapshot 是不可变的。"""
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=sample_graph_collection
        )
        with pytest.raises(ValidationError, match="Instance is frozen"):
            snapshot.world_state = {"new_key": "new_value"}
        
        with pytest.raises(TypeError, match="unhashable type"):
             {snapshot}

    def test_snapshot_store(self, sample_graph_collection: GraphCollection):
        """测试 SnapshotStore 的基本功能。"""
        store = SnapshotStore()
        s1_id, s2_id = uuid4(), uuid4()
        box1_id, box2_id = uuid4(), uuid4()

        s1 = StateSnapshot(id=s1_id, sandbox_id=box1_id, graph_collection=sample_graph_collection)
        s2 = StateSnapshot(id=s2_id, sandbox_id=box1_id, graph_collection=sample_graph_collection)

        store.save(s1)
        store.save(s2)

        assert store.get(s1_id) == s1
        assert store.get(uuid4()) is None
        assert len(store.find_by_sandbox(box1_id)) == 2
        assert len(store.find_by_sandbox(box2_id)) == 0
        with pytest.raises(ValueError, match=f"Snapshot with id {s1_id} already exists"):
            store.save(s1)


# ---------------------------------------------------------------------------
# Section 3: Dependency Parser (`core/dependency_parser.py`)
# - 这部分测试不受影响，因为解析器在宏求值前运行，并且只关心 `{{ nodes.* }}` 语法。
# ---------------------------------------------------------------------------

class TestDependencyParser:
    """测试依赖解析器 build_dependency_graph 的各种情况。"""

    def test_simple_dependency(self):
        """测试：B 依赖 A"""
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            {"id": "B", "data": {"value": "Ref: {{ nodes.A.output }}"}}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()
        assert deps["B"] == {"A"}

    def test_multiple_dependencies(self):
        """测试：C 依赖 A 和 B"""
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            {"id": "B", "data": {"runtime": "input"}},
            {"id": "C", "data": {"value": "ValA: {{ nodes.A.val }}, ValB: {{ nodes.B.val }}"}}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["C"] == {"A", "B"}
        assert deps["A"] == set()
        assert deps["B"] == set()

    def test_dependency_in_nested_structure(self):
        """测试：依赖项在深层嵌套的字典和列表中"""
        nodes = [
            {"id": "source", "data": {"runtime": "input"}},
            {"id": "consumer", "data": {
                "config": {
                    "param1": "Value from {{ nodes.source.output }}",
                    "nested_list": [1, 2, {"key": "and {{ nodes.source.another_output }}"}]
                }
            }}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["consumer"] == {"source"}

    def test_no_dependencies(self):
        """测试：节点不依赖于任何其他节点"""
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            {"id": "B", "data": {"runtime": "input"}},
        ]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()
        assert deps["B"] == set()

    def test_ignores_non_node_macros(self):
        """关键测试：解析器应忽略 {{ world.* }}, {{ run.* }} 等非节点依赖的宏"""
        nodes = [
            {"id": "A", "data": {"value": "{{ world.x + run.y + session.z }}"}}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()

    def test_dependency_on_nonexistent_node_is_ignored(self):
        """
        关键测试：依赖于图中不存在的节点（即子图的输入占位符）不应被视为依赖。
        """
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            # 节点 B 引用了 'placeholder_input'，但这个 ID 不在当前节点列表中
            {"id": "B", "data": {"value": "Got: {{ nodes.placeholder_input.value }}"}}
        ]
        deps = build_dependency_graph(nodes)
        
        # 节点 B 的依赖集应该为空，因为它引用的节点不是当前图的一部分。
        assert deps["A"] == set()
        assert deps["B"] == set()