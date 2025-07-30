# tests/test_02_building_blocks.py
import pytest
from uuid import uuid4

# ---------------------------------------------------------------------------
# 导入被测试的类和函数
# ---------------------------------------------------------------------------
from backend.core.templating import render_template
from backend.core.types import ExecutionContext
from backend.core.sandbox_models import StateSnapshot, Sandbox
from backend.models import GraphCollection
from backend.runtimes.base_runtimes import (
    InputRuntime, TemplateRuntime, LLMRuntime, SetWorldVariableRuntime
)


# ---------------------------------------------------------------------------
# Section 1: Core Fixture for Testing
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_execution_context() -> ExecutionContext:
    """
    提供一个可复用的、模拟的 ExecutionContext。
    这是本测试文件的核心 fixture，允许我们轻松地设置测试环境。
    """
    # 创建一个最小化的、有效的快照作为上下文的基础
    graph_collection = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(
        sandbox_id=uuid4(),
        graph_collection=graph_collection
    )
    # 从快照创建上下文
    context = ExecutionContext.from_snapshot(snapshot)
    return context


# ---------------------------------------------------------------------------
# Section 2: Template Rendering (`core/templating.py`)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestTemplating:
    """测试 Jinja2 模板渲染逻辑。"""

    async def test_render_accesses_all_contexts(self, mock_execution_context: ExecutionContext):
        """测试模板能否正确访问所有不同的上下文对象：nodes, world, run, session。"""
        # 准备上下文
        mock_execution_context.node_states = {
            "node_A": {"output": "Success"}
        }
        mock_execution_context.world_state = {
            "user_name": "Alice"
        }
        mock_execution_context.run_vars = {
            "trigger_input": {"message": "Do it!"}
        }
        # session_info 已经有默认值，如 start_time
        
        template_str = (
            "Node: {{ nodes.node_A.output }}, "
            "World: {{ world.user_name }}, "
            "Run: {{ run.trigger_input.message }}, "
            "Session: {{ session.start_time.year }}"
        )
        
        result = await render_template(template_str, mock_execution_context)
        
        current_year = mock_execution_context.session_info['start_time'].year
        expected = f"Node: Success, World: Alice, Run: Do it!, Session: {current_year}"
        assert result == expected

    async def test_render_without_macros(self, mock_execution_context: ExecutionContext):
        """测试不包含宏的字符串应原样返回。"""
        template_str = "This is a simple string without any macros."
        result = await render_template(template_str, mock_execution_context)
        assert result == template_str

    async def test_render_raises_error_on_missing_variable(self, mock_execution_context: ExecutionContext):
        """测试当变量不存在时，由于 StrictUndefined，渲染会抛出 IOError。"""
        template_str = "Value is {{ world.non_existent_key }}"

        with pytest.raises(IOError) as excinfo:
            await render_template(template_str, mock_execution_context)
        
        # 验证异常信息是否来自 Jinja2 的 UndefinedError
        assert "Template rendering failed" in str(excinfo.value)
        assert "'dict object' has no attribute 'non_existent_key'" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Section 3: Runtimes Unit Tests (`runtimes/base_runtimes.py`)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestBaseRuntimes:
    """对每个基础 Runtime 进行独立的单元测试。"""

    async def test_input_runtime(self):
        """测试 InputRuntime 是否正确处理输入。"""
        runtime = InputRuntime()
        # 它只关心 step_input
        result = await runtime.execute(step_input={"value": "Hello Input"})
        assert result == {"output": "Hello Input"}

    async def test_template_runtime(self, mock_execution_context: ExecutionContext):
        """测试 TemplateRuntime 是否能利用上下文进行渲染。"""
        runtime = TemplateRuntime()
        # 准备上下文
        mock_execution_context.world_state["planet"] = "Mars"
        
        # 模拟引擎调用，提供 step_input 和 context
        result = await runtime.execute(
            step_input={"template": "Hello from {{ world.planet }}"},
            pipeline_state={},
            context=mock_execution_context
        )
        
        assert result == {"output": "Hello from Mars"}

    async def test_llm_runtime(self, mock_execution_context: ExecutionContext):
        """测试 LLMRuntime 是否能从 pipeline_state 或 step_input 获取 prompt。"""
        runtime = LLMRuntime()
        
        # Case 1: prompt 来自 step_input
        result1 = await runtime.execute(
            step_input={"prompt": "Test prompt 1"},
            pipeline_state={},
            context=mock_execution_context
        )
        assert result1["llm_output"] == "LLM_RESPONSE_FOR:[Test prompt 1]"
        assert "summary" in result1

        # Case 2: prompt 来自上一步的 output，存在于 step_input
        result2 = await runtime.execute(
            step_input={"output": "Test prompt 2"},
            pipeline_state={},
            context=mock_execution_context
        )
        assert result2["llm_output"] == "LLM_RESPONSE_FOR:[Test prompt 2]"

        # Case 3: prompt 来自 pipeline_state
        result3 = await runtime.execute(
            step_input={},
            pipeline_state={"prompt": "Test prompt 3"},
            context=mock_execution_context
        )
        assert result3["llm_output"] == "LLM_RESPONSE_FOR:[Test prompt 3]"

    async def test_set_world_variable_runtime(self, mock_execution_context: ExecutionContext):
        """关键测试：验证 SetWorldVariableRuntime 能正确修改持久化的 world_state。"""
        runtime = SetWorldVariableRuntime()
        
        # 初始状态下，变量不存在
        assert "character_name" not in mock_execution_context.world_state
        
        # 模拟引擎调用
        result = await runtime.execute(
            step_input={"variable_name": "character_name", "value": "Hacker"},
            pipeline_state={},
            context=mock_execution_context
        )
        
        # 该运行时本身不应有有意义的输出
        assert result == {}
        
        # 验证副作用：上下文中的 world_state 已被修改
        assert "character_name" in mock_execution_context.world_state
        assert mock_execution_context.world_state["character_name"] == "Hacker"