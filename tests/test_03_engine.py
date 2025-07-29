# tests/test_03_engine.py

import pytest
import asyncio

from backend.models import Graph, GenericNode, Edge
from backend.core.engine import ExecutionEngine
from backend.core.registry import RuntimeRegistry, runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime


# --- Test Fixtures ---

@pytest.fixture
def fresh_runtime_registry() -> RuntimeRegistry:
    """提供一个干净的、包含基础运行时的注册表实例，避免测试间干扰。"""
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("system.template", TemplateRuntime)
    registry.register("llm.default", LLMRuntime)
    return registry

@pytest.fixture
def simple_linear_graph() -> Graph:
    """一个简单的三节点线性图：A -> B -> C"""
    return Graph(
        nodes=[
            GenericNode(id="node_A", data={"runtime": "system.input", "value": "A story about a cat."}),
            GenericNode(id="node_B", data={"runtime": "llm.default", "prompt": "Continue this story: {{ nodes.node_A.output }}"}),
            # 关键：下游节点必须使用上游节点实际输出的键名
            GenericNode(id="node_C", data={"runtime": "system.template", "template": "Final wisdom: {{ nodes.node_B.llm_output }}"})
        ],
        edges=[
            Edge(source="node_A", target="node_B"),
            Edge(source="node_B", target="node_C"),
        ],
    )

@pytest.fixture
def parallel_graph() -> Graph:
    """一个扇出图，测试并行执行：A -> B, A -> C"""
    return Graph(
        nodes=[
            GenericNode(id="A", data={"runtime": "system.input", "value": "Base Topic"}),
            GenericNode(id="B", data={"runtime": "llm.default", "prompt": "Write a poem about {{ nodes.A.output }}"}),
            GenericNode(id="C", data={"runtime": "llm.default", "prompt": "Write a joke about {{ nodes.A.output }}"}),
        ],
        edges=[
            Edge(source="A", target="B"),
            Edge(source="A", target="C"),
        ]
    )

@pytest.fixture
def graph_with_cycle() -> Graph:
    """一个包含环路的图，用于测试环路检测。"""
    return Graph(
        nodes=[
            # 修复：为每个节点提供包含 'runtime' 的合法 data
            GenericNode(id="A", data={"runtime": "system.input"}),
            GenericNode(id="B", data={"runtime": "system.input"}),
            GenericNode(id="C", data={"runtime": "system.input"}),
        ],
        edges=[
            Edge(source="A", target="B"),
            Edge(source="B", target="C"),
            Edge(source="C", target="A"), # Cycle!
        ]
    )


# --- Test Cases ---

@pytest.mark.asyncio
async def test_engine_detects_cycle(graph_with_cycle, fresh_runtime_registry: RuntimeRegistry):
    """验证引擎在图初始化时能正确检测到环路并抛出异常。"""
    executor = ExecutionEngine(registry=fresh_runtime_registry)
    with pytest.raises(ValueError, match="Cycle detected in graph"):
        await executor.execute(graph_with_cycle)


@pytest.mark.asyncio
async def test_engine_linear_flow(simple_linear_graph: Graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    """测试一个简单的线性工作流，验证数据在节点间的正确传递。"""
    mocker.patch("asyncio.sleep", return_value=None)
    executor = ExecutionEngine(registry=fresh_runtime_registry)

    final_state = await executor.execute(simple_linear_graph)

    # 验证 Node A (InputRuntime)
    assert "node_A" in final_state
    assert final_state["node_A"]["output"] == "A story about a cat."

    # 验证 Node B (LLMRuntime)
    assert "node_B" in final_state
    expected_llm_output = "LLM_RESPONSE_FOR:[Continue this story: A story about a cat.]"
    assert final_state["node_B"]["llm_output"] == expected_llm_output

    # 验证 Node C (TemplateRuntime)
    assert "node_C" in final_state
    assert final_state["node_C"]["output"] == f"Final wisdom: {expected_llm_output}"


@pytest.mark.asyncio
async def test_engine_parallel_flow(parallel_graph: Graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    """验证并行节点可以被并发执行，并且结果都正确。"""
    mocker.patch("asyncio.sleep", return_value=None)
    executor = ExecutionEngine(registry=fresh_runtime_registry)
    
    final_state = await executor.execute(parallel_graph)

    assert len(final_state) == 3
    assert "A" in final_state
    assert "B" in final_state
    assert "C" in final_state
    
    # 验证并行分支的结果
    assert final_state["B"]["llm_output"] == "LLM_RESPONSE_FOR:[Write a poem about Base Topic]"
    assert final_state["C"]["llm_output"] == "LLM_RESPONSE_FOR:[Write a joke about Base Topic]"


@pytest.mark.asyncio
async def test_engine_node_with_runtime_pipeline(fresh_runtime_registry: RuntimeRegistry, mocker):
    """测试单个节点内的运行时管道，并验证'pipeline_state'的合并行为。"""
    mocker.patch("asyncio.sleep", return_value=None)

    graph = Graph(
        nodes=[
            GenericNode(id="A", data={"runtime": "system.input", "value": "a cheerful dog"}),
            GenericNode(
                id="B",
                data={
                    "runtime": ["system.template", "llm.default"],
                    "template": "Create a story about {{ nodes.A.output }}.",
                    # 注意: LLMRuntime 会在其 step_input (即 TemplateRuntime 的输出) 中找到 'output' 作为 prompt
                }
            )
        ],
        edges=[Edge(source="A", target="B")]
    )

    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(graph)

    # 验证 B 节点的结果
    assert "B" in final_state
    node_b_result = final_state["B"]
    assert "error" not in node_b_result

    # 验证 pipeline_state 的合并行为
    expected_prompt = "Create a story about a cheerful dog."
    expected_llm_output = f"LLM_RESPONSE_FOR:[{expected_prompt}]"

    # 1. 初始配置被保留
    assert node_b_result["template"] == "Create a story about {{ nodes.A.output }}."
    # 2. TemplateRuntime 的输出被保留
    assert node_b_result["output"] == expected_prompt
    # 3. LLMRuntime 的输出也被添加进来
    assert node_b_result["llm_output"] == expected_llm_output
    assert "summary" in node_b_result


@pytest.mark.asyncio
async def test_engine_handles_runtime_error_gracefully(fresh_runtime_registry: RuntimeRegistry):
    """测试当一个节点执行失败时，引擎会记录错误并跳过下游节点。"""
    graph = Graph(
        nodes=[
            GenericNode(id="A", data={"runtime": "system.input", "value": "start"}),
            GenericNode(id="B", data={"runtime": "system.template", "template": "{{ undefined.variable }}"}), # This will fail
            GenericNode(id="C", data={"runtime": "llm.default", "prompt": "This should be skipped."}),
        ],
        edges=[
            Edge(source="A", target="B"),
            Edge(source="B", target="C"),
        ]
    )

    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(graph)

    # 验证失败的节点 B
    assert "B" in final_state
    assert "error" in final_state["B"]
    assert "Failed at step 1" in final_state["B"]["error"]
    assert "'undefined' is undefined" in final_state["B"]["error"]

    # 验证被跳过的节点 C
    assert "C" in final_state
    assert final_state["C"]["status"] == "skipped"
    assert final_state["C"]["reason"] == "Upstream failure of node B."