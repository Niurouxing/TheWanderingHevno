# tests/test_core_contracts.py

import pytest
from pydantic import ValidationError
from uuid import uuid4


from plugins.core_engine.contracts import (
    GraphCollection,
    GenericNode,
    RuntimeInstruction,
    StateSnapshot,
    Sandbox,
)

class TestCoreModels:
    """测试核心数据模型，这些模型是所有插件共享的契约。"""

    # Migrated from test_01_foundations.py
    def test_runtime_instruction_validation(self):
        inst = RuntimeInstruction(runtime="test.runtime", config={"key": "value"})
        assert inst.runtime == "test.runtime"
        with pytest.raises(ValidationError):
            RuntimeInstruction(config={})

    # Migrated from test_01_foundations.py
    def test_generic_node_validation_success(self):
        node = GenericNode(
            id="n1",
            run=[{"runtime": "step1"}, {"runtime": "step2"}]
        )
        assert len(node.run) == 2
        assert isinstance(node.run[0], RuntimeInstruction)

    # Migrated from test_01_foundations.py
    def test_graph_collection_validation(self):
        valid_data = {"main": {"nodes": [{"id": "a", "run": []}]}}
        collection = GraphCollection.model_validate(valid_data)
        assert "main" in collection.root

        with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate({"other": {"nodes": []}})

class TestSandboxModels:
    """测试沙盒和快照模型。"""

    # Migrated from test_01_foundations.py
    @pytest.fixture
    def sample_graph_collection(self) -> GraphCollection:
        return GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "run": []}]}})

    def test_state_snapshot_is_immutable(self, sample_graph_collection: GraphCollection):
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=sample_graph_collection)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            snapshot.world_state = {"new_key": "new_value"}