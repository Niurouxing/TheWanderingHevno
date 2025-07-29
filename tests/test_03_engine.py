# tests/test_03_executor.py
import pytest
import asyncio
from unittest.mock import call, ANY
from backend.models import Graph, GenericNode, Edge 
from backend.core.engine import ExecutionEngine
from backend.core.registry import RuntimeRegistry

# --- 测试基础线性流程 ---
@pytest.mark.asyncio
async def test_executor_linear_flow(simple_linear_graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    mocker.patch("backend.runtimes.base_runtimes.asyncio.sleep", return_value=None)
    executor = ExecutionEngine(registry=fresh_runtime_registry)

    final_state = await executor.execute(simple_linear_graph)

    assert "node_A" in final_state
    assert final_state["node_A"]["output"] == "A story about a cat."

    assert "node_B" in final_state
    # 修复：LLMRuntime 的输出键是 'llm_output'
    expected_llm_output = f"LLM_RESPONSE_FOR:[Continue this story: A story about a cat.]"
    assert final_state["node_B"]["llm_output"] == expected_llm_output
    
    # 获取测试图中的 Node C 并修改其模板
    node_c_config = simple_linear_graph.nodes[2].data
    node_c_config['template'] = 'Final wisdom: {{ nodes.node_B.llm_output }}'

    # 重新执行
    final_state = await executor.execute(simple_linear_graph)

    assert "node_C" in final_state
    assert final_state["node_C"]["output"] == f"Final wisdom: {expected_llm_output}"

# --- 测试并行执行 ---
@pytest.mark.asyncio
async def test_executor_parallel_flow(parallel_graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    """验证并行节点是否可以被并发执行"""
    call_order = []
    
    # 我们直接 mock _execute_node 方法，这样控制力最强
    original_execute_node = ExecutionEngine._execute_node
    
    async def mock_execute_node_tracked(self, node, context):
        # 如果是需要等待的节点，记录其ID
        if node.id in ['B', 'C']:
            call_order.append(node.id)
            await asyncio.sleep(0.1) # 模拟耗时
        
        return await original_execute_node(self, node, context)

    mocker.patch("backend.core.engine.ExecutionEngine._execute_node", side_effect=mock_execute_node_tracked, autospec=True)

    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(parallel_graph)

    # 断言结果
    assert "B" in final_state and "llm_output" in final_state["B"]
    assert "C" in final_state and "llm_output" in final_state["C"]

    # 可以添加更详细的断言
    assert final_state["B"]["llm_output"] == "LLM_RESPONSE_FOR:[Write a poem about Base Topic]"
    assert final_state["C"]["llm_output"] == "LLM_RESPONSE_FOR:[Write a joke about Base Topic]"

# --- 测试分支合并 ---
@pytest.mark.asyncio
async def test_executor_fan_in_flow(fan_in_graph, fresh_runtime_registry: RuntimeRegistry):
    """验证合并节点是否会等待所有上游节点完成"""
    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(fan_in_graph)

    # A 和 B 的输出应该都准备好了
    assert final_state["A"]["output"] == "Character: Knight"
    assert final_state["B"]["output"] == "Action: Fights a dragon"
    
    # C 应该成功地从 A 和 B 渲染了模板
    assert final_state["C"]["output"] == "Story: The Character: Knight Action: Fights a dragon."

@pytest.mark.asyncio
async def test_executor_handles_runtime_error(simple_linear_graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    """验证当一个节点出错时，下游节点会被正确标记为skipped"""
    mocker.patch(
        "backend.runtimes.base_runtimes.LLMRuntime.execute",
        side_effect=ValueError("LLM API is down")
    )
    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(simple_linear_graph)

    # A 应该成功执行
    assert "node_A" in final_state and "output" in final_state["node_A"]
    
    # B 应该记录了错误
    assert "node_B" in final_state and "error" in final_state["node_B"]
    assert "LLM API is down" in final_state["node_B"]["error"]

    # 关键修复：我们现在期望 node_C 存在，并且状态为 'skipped'
    assert "node_C" in final_state
    assert final_state["node_C"].get("status") == "skipped"
    assert "Upstream failure" in final_state["node_C"].get("reason", "")

@pytest.mark.asyncio
async def test_executor_detects_cycle(cyclic_graph, fresh_runtime_registry: RuntimeRegistry):
    """验证执行器能否正确处理带环的图"""
    executor = ExecutionEngine(registry=fresh_runtime_registry)
    
    # 解决方案：测试代码保持不变，但现在它依赖于 executor 中正确的异常处理
    with pytest.raises(ValueError, match="Graph has a cycle"):
        await executor.execute(cyclic_graph)

@pytest.mark.asyncio
async def test_node_with_runtime_pipeline(mocker, fresh_runtime_registry: RuntimeRegistry):
    """测试单个节点内的运行时管道是否按顺序执行。"""
    mocker.patch("backend.runtimes.base_runtimes.asyncio.sleep", return_value=None)
    
    # 这个节点先用template准备prompt，再用llm调用
    graph = Graph(
        nodes=[
            GenericNode(id="A", type="input", data={"runtime": "system.input", "value": "a cheerful dog"}),
            GenericNode(
                id="B",
                type="default",
                data={
                    "runtime": ["system.template", "llm.default"],
                    "template": "Create a story about {{ nodes.A.output }}."
                }
            )
        ],
        # 关键修复：添加 B 依赖 A 的边
        edges=[Edge(source="A", target="B")] 
    )

    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(graph)

    assert "B" in final_state
    assert "error" not in final_state["B"]

    # 最终的 `pipeline_state` 是合并的结果，它会包含所有步骤的输出。
    # `TemplateRuntime` 输出 `{"output": "..."}`
    # `LLMRuntime` 输出 `{"llm_output": "...", "summary": "..."}`
    # 合并后，`final_state["B"]` 会同时包含 "output" 和 "llm_output" 键。
    
    expected_prompt = "Create a story about a cheerful dog."
    expected_llm_output = f"LLM_RESPONSE_FOR:[{expected_prompt}]"

    # 断言 TemplateRuntime 的中间输出仍然存在于最终状态中
    assert final_state["B"]["output"] == expected_prompt
    
    # 断言 LLMRuntime 的最终输出也存在
    assert final_state["B"]["llm_output"] == expected_llm_output


@pytest.mark.asyncio
async def test_runtime_pipeline_failure(mocker, fresh_runtime_registry: RuntimeRegistry):
    """测试管道中一步失败时，节点是否正确报告错误。"""
    # 让TemplateRuntime渲染一个不存在的变量，使其失败
    graph = Graph(
        nodes=[
            GenericNode(
                id="C",
                type="default",
                data={
                    "runtime": ["system.template", "llm.default"],
                    "template": "This will fail: {{ non_existent.var }}"
                }
            )
        ],
        edges=[]
    )
    
    executor = ExecutionEngine(registry=fresh_runtime_registry)
    final_state = await executor.execute(graph)

    assert "C" in final_state
    assert "error" in final_state["C"]
    assert "Failed at step 1" in final_state["C"]["error"]
    assert final_state["C"]["runtime"] == "system.template"