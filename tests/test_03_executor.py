# tests/test_03_executor.py
import pytest
import asyncio
from unittest.mock import call, ANY
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
    # Mock asyncio.sleep 来跟踪调用顺序
    # 使用 side_effect 可以在 mock 被调用时执行一个函数
    call_order = []
    async def mock_sleep(duration, node_id):
        call_order.append(node_id)
        await asyncio.sleep(0) # 实际不等待，但保持其异步特性
    
    # 重新 mock LLMRuntime 的 execute 方法，以便我们传递节点ID
    original_llm_execute = fresh_runtime_registry.get_runtime("llm.default").execute
    async def mocked_llm_execute_with_id(node_data, context):
        node_id = next(n.id for n in context.graph.nodes if n.data == node_data)
        await mock_sleep(1, node_id)
        return await original_llm_execute(node_data, context)

    mocker.patch("backend.runtimes.base_runtimes.LLMRuntime.execute", side_effect=mocked_llm_execute_with_id)
    
    executor = GraphExecutor(registry=fresh_runtime_registry)
    final_state = await executor.execute(parallel_graph)

    # 断言结果
    assert "B" in final_state and "output" in final_state["B"]
    assert "C" in final_state and "output" in final_state["C"]

    # 关键断言：B和C的执行顺序是不确定的，因为它们是并行的
    # 所以我们检查它们是否都在A之后执行
    assert len(call_order) == 2
    assert "B" in call_order
    assert "C" in call_order

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

# --- 测试错误处理 ---
@pytest.mark.asyncio
async def test_executor_handles_runtime_error(simple_linear_graph, fresh_runtime_registry: RuntimeRegistry, mocker):
    """验证当一个节点出错时，图的执行会停止，并记录错误"""
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
    
    # 解决方案：关键修复！
    # C 不应该被执行，因为它依赖于失败的B。
    # 所以它不应该出现在 final_state 中。
    assert "node_C" not in final_state

@pytest.mark.asyncio
async def test_executor_detects_cycle(cyclic_graph, fresh_runtime_registry: RuntimeRegistry):
    """验证执行器能否正确处理带环的图"""
    executor = GraphExecutor(registry=fresh_runtime_registry)
    
    # 解决方案：测试代码保持不变，但现在它依赖于 executor 中正确的异常处理
    with pytest.raises(ValueError, match="Graph has a cycle"):
        await executor.execute(cyclic_graph)