# tests/test_04_templating.py
import pytest
from backend.core.templating import render_template
from backend.core.runtime import ExecutionContext
from backend.models import Graph, GenericNode

@pytest.mark.asyncio
async def test_render_simple_variable_access():
    """测试基本的节点输出访问 {{ nodes.NODE_ID.OUTPUT_KEY }}"""
    context = ExecutionContext(
        state={"node_A": {"output": "Success"}},
        graph=None,
    )
    template_str = "The result from node A is: {{ nodes.node_A.output }}"
    result = await render_template(template_str, context)
    assert result == "The result from node A is: Success"

@pytest.mark.asyncio
async def test_render_session_and_global_vars_access():
    """测试访问会话信息和全局变量"""
    context = ExecutionContext(
        state={},
        graph=None,
        session_info={"conversation_turn": 3},
        global_vars={"user_name": "Alice"}
    )
    template_str = "User: {{ vars.user_name }}, Turn: {{ session.conversation_turn }}"
    result = await render_template(template_str, context)
    assert result == "User: Alice, Turn: 3"
    
@pytest.mark.asyncio
async def test_render_missing_variable_gracefully():
    """测试当变量不存在时，Jinja2默认返回空字符串，而不是抛出异常"""
    context = ExecutionContext(state={}, graph=None)
    template_str = "Value is {{ nodes.non_existent.output }}"
    result = await render_template(template_str, context)
    assert result == "Value is " # Jinja2 将未定义的变量渲染为空字符串

@pytest.mark.asyncio
async def test_render_no_macros():
    """测试没有宏的模板应该原样返回"""
    context = ExecutionContext(state={}, graph=None)
    template_str = "This is a plain string with no macros."
    result = await render_template(template_str, context)
    assert result == template_str

@pytest.mark.asyncio
async def test_render_complex_template():
    """测试混合使用多种变量"""
    context = ExecutionContext(
        state={"story_start": {"text": "Once upon a time..."}},
        graph=None,
        session_info={"conversation_turn": 1},
        global_vars={"theme": "fantasy"}
    )
    template_str = """
    Turn: {{ session.conversation_turn }}
    Theme: {{ vars.theme }}
    Story: {{ nodes.story_start.text }}
    """
    expected_output = """
    Turn: 1
    Theme: fantasy
    Story: Once upon a time...
    """
    result = await render_template(template_str, context)
    assert result.strip() == expected_output.strip()