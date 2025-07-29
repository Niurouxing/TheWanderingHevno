# tests/test_01_models.py
import pytest
from pydantic import ValidationError
from backend.models import GenericNode, Graph

def test_generic_node_validation():
    # 有效数据
    valid_data = {"id": "1", "type": "default", "data": {"runtime": "test"}}
    node = GenericNode(**valid_data)
    assert node.id == "1"
    assert node.data["runtime"] == "test"

    # 缺少 runtime 会导致 data 字段验证失败（虽然我们没有明确要求，但通常是需要的）
    # Pydantic 默认所有字段都是必须的，除非有默认值或 Optional
    # 但我们这里是data字段本身必须存在，其内容可以灵活
    valid_data_no_runtime = {"id": "2", "type": "default", "data": {}}
    node_no_runtime = GenericNode(**valid_data_no_runtime)
    assert node_no_runtime.data == {}


    # 缺少 id 字段应该会失败
    with pytest.raises(ValidationError):
        GenericNode(type="default", data={"runtime": "test"})

def test_graph_model(simple_linear_graph): # 使用我们定义的fixture
    """测试Graph模型能否正确加载一个合法的图结构。"""
    graph = simple_linear_graph
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.nodes[0].id == "node_A"