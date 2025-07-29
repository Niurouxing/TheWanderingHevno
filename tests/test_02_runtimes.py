# tests/test_02_runtimes.py
import pytest
from backend.core.runtime import ExecutionContext
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime

# ---- 测试 InputRuntime ----
@pytest.mark.asyncio
async def test_input_runtime():
    runtime = InputRuntime()
    node_data = {"value": "Hello World"}
    context = ExecutionContext(state={}, graph=None, function_registry={})
    
    result = await runtime.execute(node_data, context)
    
    assert result == {"output": "Hello World"}

# ---- 测试 TemplateRuntime ----
@pytest.mark.asyncio
async def test_template_runtime_simple():
    runtime = TemplateRuntime()
    node_data = {"template": "The value is: {{ nodes.node_A.output }}"}
    context = ExecutionContext(
        state={"node_A": {"output": "SUCCESS"}},
        graph=None,
        function_registry={}
    )
    
    result = await runtime.execute(node_data, context)
    
    assert result == {"output": "The value is: SUCCESS"}

# tests/test_02_runtimes.py
@pytest.mark.asyncio
async def test_template_runtime_handles_missing_variable_gracefully():
    # 测试名和逻辑都变了
    runtime = TemplateRuntime()
    # 使用一个更复杂的缺失路径来测试 ChainableUndefined
    node_data = {"template": "Value: {{ nodes.non_existent.output.text }}"}
    context = ExecutionContext(state={}, graph=None, function_registry={})

    # 解决方案：断言它能成功执行并返回预期结果（空字符串）
    result = await runtime.execute(node_data, context)
    assert result['output'] == "Value: "

# ---- 测试 LLMRuntime (关键：使用 Mock) ----
@pytest.mark.asyncio
async def test_llm_runtime_with_mock(mocker): # 使用 pytest-mock 的 mocker fixture
    # 1. Mock掉真正的LLM调用（这里我们假设它是一个异步函数）
    # 注意：我们mock的是它在运行时模块中被调用的地方
    mocked_llm_call = mocker.patch(
        "backend.runtimes.base_runtimes.asyncio.sleep", # 在MVP中我们用sleep模拟
        return_value=None # asyncio.sleep不返回任何东西
    )
    
    runtime = LLMRuntime()
    node_data = {"prompt": "Summarize: {{ nodes.input.text }}"}
    context = ExecutionContext(
        state={"input": {"text": "A very long story."}},
        graph=None,
        function_registry={}
    )
    
    result = await runtime.execute(node_data, context)

    # 2. 断言结果是否基于模拟的 LLM 响应
    expected_prompt = "Summarize: A very long story."
    assert "output" in result
    assert result["output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"
    assert "summary" in result

    # 3. 断言 mock 的函数是否被调用了
    mocked_llm_call.assert_awaited_once_with(1)