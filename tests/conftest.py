# tests/conftest.py
import pytest
from backend.core.registry import RuntimeRegistry
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime
from backend.models import Graph, GenericNode, Edge

@pytest.fixture(scope="function") # 'function' scope表示每个测试函数都会获得一个新的实例
def fresh_runtime_registry():
    """提供一个干净的、预填充了基础运行时的注册表实例。"""
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("system.template", TemplateRuntime)
    registry.register("llm.default", LLMRuntime)
    return registry

@pytest.fixture
def simple_linear_graph():
    """一个简单的线性图，用于测试执行流程。"""
    return Graph(
        nodes=[
            GenericNode(id='node_A', type='input', data={'runtime': 'system.input', 'value': 'A story about a cat.'}),
            # 关键修复: '{{ node_A.output }}' -> '{{ nodes.node_A.output }}'
            GenericNode(id='node_B', type='default', data={'runtime': 'llm.default', 'prompt': 'Continue this story: {{ nodes.node_A.output }}'}),
            # 关键修复: '{{ node_B.output }}' -> '{{ nodes.node_B.output }}'
            GenericNode(id='node_C', type='output', data={'runtime': 'system.template', 'template': 'The final story is: {{ nodes.node_B.output }}'}),
        ],
        edges=[
            Edge(source='node_A', target='node_B'),
            Edge(source='node_B', target='node_C'),
        ]
    )

@pytest.fixture
def parallel_graph():
    """提供一个并行的图，用于测试并发执行"""
    return Graph(
        nodes=[
            GenericNode(id='A', type='input', data={"runtime": "system.input", "value": "Base Topic"}),
            # 修复模板变量路径
            GenericNode(id='B', type='default', data={"runtime": "llm.default", "prompt": "Write a poem about {{ nodes.A.output }}"}),
            GenericNode(id='C', type='default', data={"runtime": "llm.default", "prompt": "Write a joke about {{ nodes.A.output }}"}),
        ],
        edges=[
            Edge(source='A', target='B'),
            Edge(source='A', target='C'),
        ]
    )

@pytest.fixture
def fan_in_graph():
    """一个分支合并的图 (fan-in)。"""
    return Graph(
        nodes=[
            GenericNode(id="A", type="input", data={"runtime": "system.input", "value": "Character: Knight"}),
            GenericNode(id="B", type="input", data={"runtime": "system.input", "value": "Action: Fights a dragon"}),
            GenericNode(id="C", type="output", data={
                "runtime": "system.template", 
                # 关键修复
                "template": "Story: The {{ nodes.A.output }} {{ nodes.B.output }}."
            }),
        ],
        edges=[
            Edge(source="A", target="C"),
            Edge(source="B", target="C"),
        ]
    )
@pytest.fixture
def cyclic_graph():
    """一个包含环路的图，用于测试错误处理。 A -> B -> A"""
    return Graph(
        nodes=[
            GenericNode(id="A", type="default", data={"runtime": "system.template", "template": "{{ B.output }}"}),
            GenericNode(id="B", type="default", data={"runtime": "system.template", "template": "{{ A.output }}"}),
        ],
        edges=[
            Edge(source="A", target="B"),
            Edge(source="B", target="A"),
        ]
    )