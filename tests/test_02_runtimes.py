# tests/test_02_runtimes.py
import pytest
import asyncio 
from backend.core.runtime import ExecutionContext
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime

@pytest.mark.asyncio
async def test_input_runtime():
    runtime = InputRuntime()
    # 模拟 kwargs
    kwargs = {
        "step_input": {"value": "Hello World"}
    }
    result = await runtime.execute(**kwargs)
    assert result == {"output": "Hello World"}


@pytest.mark.asyncio
async def test_template_runtime_simple():
    runtime = TemplateRuntime()
    context = ExecutionContext(
        state={"node_A": {"output": "SUCCESS"}},
        graph=None
    )
    # 模拟 kwargs
    kwargs = {
        "step_input": {"template": "The value is: {{ nodes.node_A.output }}"},
        "pipeline_state": {"template": "The value is: {{ nodes.node_A.output }}"},
        "context": context
    }
    result = await runtime.execute(**kwargs)
    assert result == {"output": "The value is: SUCCESS"}


@pytest.mark.asyncio
async def test_template_runtime_raises_error_on_missing_variable():
    runtime = TemplateRuntime()
    context = ExecutionContext(state={}, graph=None)
    # 模拟 kwargs
    kwargs = {
        "step_input": {"template": "Value: {{ non_existent.var }}"},
        "pipeline_state": {"template": "Value: {{ non_existent.var }}"},
        "context": context
    }
    # 在 3.10+ 中，Jinja2 抛出的异常是 jinja2.UndefinedError
    # IOError 是我们之前自定义的包装，可以根据实际情况调整
    # 假设 templating.py 中仍然包装为 IOError
    with pytest.raises(IOError, match="Template rendering failed: 'non_existent' is undefined"):
        await runtime.execute(**kwargs)


@pytest.mark.asyncio
async def test_llm_runtime_with_mock(mocker):
    mocked_sleep = mocker.patch("asyncio.sleep", return_value=None)
    
    runtime = LLMRuntime()
    context = ExecutionContext(
        state={"input": {"text": "A very long story."}},
        graph=None
    )
    # 模拟 kwargs
    kwargs = {
        "step_input": {"prompt": "Summarize: {{ nodes.input.text }}"},
        "pipeline_state": {"prompt": "Summarize: {{ nodes.input.text }}"},
        "context": context
    }
    result = await runtime.execute(**kwargs)

    expected_prompt = "Summarize: A very long story."
    assert "llm_output" in result
    assert "summary" in result
    assert result["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"
    
    mocked_sleep.assert_called_once_with(0.1)