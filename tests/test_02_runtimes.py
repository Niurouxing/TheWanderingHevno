# tests/test_02_runtimes.py
import pytest
from backend.core.runtime import ExecutionContext
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime

# ---- 测试 InputRuntime ----
@pytest.mark.asyncio
async def test_input_runtime():
    runtime = InputRuntime()
    node_data = {"value": "Hello World"}
    context = ExecutionContext(state={}, graph=None) # function_registry 是可选的

    result = await runtime.execute(node_data, node_data, context)
    
    assert result == {"output": "Hello World"}

# ---- 测试 TemplateRuntime ----
@pytest.mark.asyncio
async def test_template_runtime_simple():
    runtime = TemplateRuntime()
    node_data = {"template": "The value is: {{ nodes.node_A.output }}"}
    context = ExecutionContext(
        state={"node_A": {"output": "SUCCESS"}},
        graph=None,
    )

    # 修复：使用新的接口签名
    result = await runtime.execute(node_data, node_data, context)
    
    assert result == {"output": "The value is: SUCCESS"}

# tests/test_02_runtimes.py
@pytest.mark.asyncio
async def test_template_runtime_raises_error_on_missing_variable():
    """
    测试当模板变量缺失时，TemplateRuntime会因为渲染失败而抛出IOError。
    这个错误会在Executor层面被捕获并记录。
    但我们在这里测试的是运行时本身的直接行为。
    """
    runtime = TemplateRuntime()
    node_data = {"template": "Value: {{ non_existent.var }}"}
    context = ExecutionContext(state={}, graph=None)

    # 修复：在 with 块内使用新的接口签名
    with pytest.raises(IOError, match="Template rendering failed: 'non_existent' is undefined"):
        await runtime.execute(node_data, node_data, context)


# ---- 测试 LLMRuntime (关键：使用 Mock) ----
@pytest.mark.asyncio
async def test_llm_runtime_with_mock(mocker): # 使用 pytest-mock 的 mocker fixture
    # 1. Mock掉真正的LLM调用（这里我们假设它是一个异步函数）
    # 注意：我们mock的是它在运行时模块中被调用的地方
    mocked_llm_call = mocker.patch(
        "backend.runtimes.base_runtimes.asyncio.sleep",
        return_value=None
    )

    runtime = LLMRuntime()
    node_data = {"prompt": "Summarize: {{ nodes.input.text }}"}
    context = ExecutionContext(
        state={"input": {"text": "A very long story."}},
        graph=None
    )

    # 修复：使用新的接口签名
    result = await runtime.execute(node_data, node_data, context)

    # 修复：断言新的输出键名
    expected_prompt = "Summarize: A very long story."
    assert result == {
        "llm_output": f"LLM_RESPONSE_FOR:[{expected_prompt}]",
        "summary": f"Summary of '{expected_prompt[:20]}...'"
    }
    mocked_llm_call.assert_called_once_with(0.1)