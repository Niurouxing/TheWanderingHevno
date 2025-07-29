# tests/test_01_models.py
import pytest
from pydantic import ValidationError
from backend.models import GenericNode, Graph

def test_generic_node_validation():
    # 1. 测试有效数据
    valid_data = {"id": "1", "type": "default", "data": {"runtime": "test"}}
    node = GenericNode(**valid_data)
    assert node.id == "1"
    assert node.data["runtime"] == "test"

    # 2. 测试 data 中没有 runtime 的情况，这应该会失败
    with pytest.raises(ValidationError, match="must contain a 'runtime' field"):
        GenericNode(id="2", type="default", data={})

    # 3. 测试 runtime 值类型不正确的情况
    with pytest.raises(ValidationError, match="must be a string or a list of strings"):
        GenericNode(id="3", type="default", data={"runtime": 123})

    # 4. 测试 runtime 是一个包含非字符串的列表
    with pytest.raises(ValidationError, match="must be a string or a list of strings"):
        GenericNode(id="4", type="default", data={"runtime": ["test", 123]})

def test_graph_model(simple_linear_graph): # 使用我们定义的fixture
    """测试Graph模型能否正确加载一个合法的图结构。"""
    graph = simple_linear_graph
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.nodes[0].id == "node_A"