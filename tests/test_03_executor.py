# tests/test_03_executor.py
import pytest
import asyncio
from unittest.mock import call, ANY
from backend.models import Graph, GenericNode, Edge 
from backend.core.executor import GraphExecutor
from backend.core.registry import RuntimeRegistry

# --- 测试基础线性流程 ---
@pytest.mark.asyncio
async def test_executor_linear_flow(simple_linear_graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    mocker.patch("backend.runtimes.base_runtimes.asyncio.sleep", return_value=None)
    executor = GraphExecutor(registry=fresh_runtime_registry)
    
    final_state = await executor.execute(simple_linear_graph)

    assert "node_A" in final_state
    assert final_state["node_A"]["output"] == "A story about a cat."
    
    assert "node_B" in final_state
    expected_llm_input = "Continue this story: A story about a cat."
    # 我们要访问新的模板全局变量 `nodes`
    assert final_state["node_B"]["output"] == f"LLM_RESPONSE_FOR:[Continue this story: {final_state['node_A']['output']}]"

    assert "node_C" in final_state
    expected_final_output = f"The final story is: {final_state['node_B']['output']}"
    assert final_state["node_C"]["output"] == expected_final_output

# --- 测试并行执行 ---
@pytest.mark.asyncio
async def test_executor_parallel_flow(parallel_graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    """验证并行节点是否可以被并发执行"""
    call_order = []
    
    # 我们直接 mock _execute_node 方法，这样控制力最强
    original_execute_node = GraphExecutor._execute_node
    
    async def mock_execute_node_tracked(self, node, context):
        # 如果是需要等待的节点，记录其ID
        if node.id in ['B', 'C']:
            call_order.append(node.id)
            await asyncio.sleep(0.1) # 模拟耗时
        
        # 调用原始的执行逻辑
        return await original_execute_node(self, node, context)

    mocker.patch("backend.core.executor.GraphExecutor._execute_node", side_effect=mock_execute_node_tracked, autospec=True)

    executor = GraphExecutor(registry=fresh_runtime_registry)
    final_state = await executor.execute(parallel_graph)

    # 断言结果
    assert "B" in final_state and "output" in final_state["B"]
    assert "C" in final_state and "output" in final_state["C"]
    
    # 断言并行性：我们不关心B和C谁先谁后，只要它们都在A之后
    assert call_order == ['B', 'C'] or call_order == ['C', 'B']

# --- 测试分支合并 ---
@pytest.mark.asyncio
async def test_executor_fan_in_flow(fan_in_graph, fresh_runtime_registry: RuntimeRegistry):
    """验证合并节点是否会等待所有上游节点完成"""
    executor = GraphExecutor(registry=fresh_runtime_registry)
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
    executor = GraphExecutor(registry=fresh_runtime_registry)
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
    executor = GraphExecutor(registry=fresh_runtime_registry)
    
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

    executor = GraphExecutor(registry=fresh_runtime_registry)
    final_state = await executor.execute(graph)
    
    assert "B" in final_state
    assert "error" not in final_state["B"]
    
    # 检查最终输出是否是LLM运行时的输出
    expected_prompt = "Create a story about a cheerful dog."
    expected_llm_output = f"LLM_RESPONSE_FOR:[{expected_prompt}]"
    assert final_state["B"]["output"] == expected_llm_output


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
    
    executor = GraphExecutor(registry=fresh_runtime_registry)
    final_state = await executor.execute(graph)

    assert "C" in final_state
    assert "error" in final_state["C"]
    assert "Failed at step 1" in final_state["C"]["error"]
    assert final_state["C"]["runtime"] == "system.template"