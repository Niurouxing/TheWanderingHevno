# tests/test_02_evaluation_unit.py
import pytest
from uuid import uuid4
from backend.core.utils import DotAccessibleDict

# ---------------------------------------------------------------------------
# 导入被测试的类和函数
# ---------------------------------------------------------------------------
from backend.core.evaluation import (
    evaluate_expression, evaluate_data, build_evaluation_context
)
from backend.core.types import ExecutionContext
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection
from backend.runtimes.base_runtimes import (
    InputRuntime, LLMRuntime, SetWorldVariableRuntime
)
from backend.runtimes.control_runtimes import ExecuteRuntime


# ---------------------------------------------------------------------------
# Section 1: Core Fixture for Testing
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_exec_context() -> ExecutionContext:
    """
    提供一个可复用的、模拟的 ExecutionContext。
    这是本测试文件的核心 fixture，用于构建宏的求值环境。
    """
    graph_collection = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_collection)
    context = ExecutionContext.from_snapshot(snapshot)
    
    # 预填充一些数据以供测试
    context.node_states = {"node_A": {"output": "Success"}}
    context.world_state = {"user_name": "Alice", "hp": 100}
    context.run_vars = {"trigger_input": {"message": "Do it!"}}
    
    return context

@pytest.fixture
def mock_eval_context(mock_exec_context: ExecutionContext) -> dict:
    """提供一个扁平化的、用于宏执行的字典上下文。"""
    return build_evaluation_context(mock_exec_context)


# ---------------------------------------------------------------------------
# Section 2: Macro Evaluation Core (`core/evaluation.py`)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEvaluationCore:
    """对宏求值核心 `evaluate_expression` 进行深度单元测试。"""

    async def test_simple_expressions(self, mock_eval_context):
        """测试简单的 Python 表达式求值。"""
        assert await evaluate_expression("1 + 1", mock_eval_context) == 2
        assert await evaluate_expression("'hello' + ' ' + 'world'", mock_eval_context) == "hello world"
        assert await evaluate_expression("True and False", mock_eval_context) is False

    async def test_context_access(self, mock_eval_context):
        """测试宏能否正确访问所有上下文对象：nodes, world, run, session。"""
        code = "f'{nodes.node_A.output}, {world.user_name}, {run.trigger_input.message}'"
        result = await evaluate_expression(code, mock_eval_context)
        assert result == "Success, Alice, Do it!"

    async def test_side_effects_on_world_state(self, mock_eval_context):
        """关键测试：验证宏可以修改传入的上下文（特别是 world_state）。"""
        assert mock_eval_context["world"]["hp"] == 100
        # 这个宏没有返回值，但有副作用
        await evaluate_expression("world['hp'] -= 10", mock_eval_context)
        assert mock_eval_context["world"]["hp"] == 90

    async def test_multiline_script_with_return(self, mock_eval_context):
        """测试多行脚本，并验证最后一行表达式作为返回值。"""
        # 修正代码：使用一个明确的变量来存储结果
        code = """
x = 10
y = 20
if world.hp > 50:
    result = x + y
else:
    result = x - y
result  # 最后一行的表达式将被作为返回值
"""
        mock_eval_context["world"]["hp"] = 80
        # 现在这个测试应该能通过了
        assert await evaluate_expression(code, mock_eval_context) == 30
        
        mock_eval_context["world"]["hp"] = 40
        assert await evaluate_expression(code, mock_eval_context) == -10

    async def test_syntax_error_handling(self, mock_eval_context):
        """测试 Python 语法错误会被捕获并引发 ValueError。"""
        with pytest.raises(ValueError, match="Macro syntax error"):
            await evaluate_expression("1 +", mock_eval_context)

    async def test_runtime_error_handling(self, mock_eval_context):
        """测试 Python 运行时错误（如 NameError）会直接抛出。"""
        with pytest.raises(NameError):
            await evaluate_expression("non_existent_variable", mock_eval_context)

@pytest.mark.asyncio
class TestRecursiveEvaluation:
    """对递归求值函数 `evaluate_data` 进行测试。"""

    async def test_evaluate_data_recursively(self, mock_eval_context):
        """测试 `evaluate_data` 能否正确处理嵌套的字典和列表。"""
        data_structure = {
            "static_string": "I am static.",
            "direct_macro": "{{ 1 + 2 }}",
            "nested_list": [
                10,
                "{{ world.user_name }}",
                {"deep_macro": "{{ nodes.node_A.output.lower() }}"}
            ],
            "nested_dict": {
                "another_macro": "{{ 'nested ' * 2 }}"
            }
        }
        
        result = await evaluate_data(data_structure, mock_eval_context)
        
        expected = {
            "static_string": "I am static.",
            "direct_macro": 3,
            "nested_list": [
                10,
                "Alice",
                {"deep_macro": "success"}
            ],
            "nested_dict": {
                "another_macro": "nested nested "
            }
        }
        assert result == expected

    async def test_evaluate_data_non_macro_string(self, mock_eval_context):
        """测试不符合宏格式的字符串应该原样返回。"""
        assert await evaluate_data("Just a string", mock_eval_context) == "Just a string"
        assert await evaluate_data("{ not a macro }", mock_eval_context) == "{ not a macro }"


# ---------------------------------------------------------------------------
# Section 3: Runtimes Unit Tests (New Architecture)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRuntimesWithMacros:
    """对每个运行时进行独立的单元测试，假设宏预处理已完成。"""

    async def test_input_runtime(self):
        """InputRuntime 的行为不变。"""
        runtime = InputRuntime()
        result = await runtime.execute(step_input={"value": "Hello Input"})
        assert result == {"output": "Hello Input"}

    async def test_llm_runtime_simplified(self):
        """测试 LLMRuntime，它现在接收的是【已渲染好】的 prompt。"""
        runtime = LLMRuntime()
        
        # 宏预处理器已经完成了工作，LLMRuntime 接收到的就是最终字符串。
        result = await runtime.execute(
            step_input={"prompt": "A fully rendered prompt about Mars."},
            pipeline_state={"prompt": "A fully rendered prompt about Mars."},
            context=None # LLMRuntime 不再直接使用 context
        )
        
        assert result["llm_output"] == "LLM_RESPONSE_FOR:[A fully rendered prompt about Mars.]"
        assert "summary" in result

    async def test_set_world_variable_runtime(self, mock_exec_context: ExecutionContext):
        """测试 SetWorldVariableRuntime，它的输入值现在由宏预先计算。"""
        runtime = SetWorldVariableRuntime()
        
        assert "character_name" not in mock_exec_context.world_state
        
        # 模拟引擎调用，step_input 已经是宏求值后的结果。
        result = await runtime.execute(
            step_input={"variable_name": "character_name", "value": "Hacker"},
            context=mock_exec_context
        )
        
        assert result == {}
        assert mock_exec_context.world_state["character_name"] == "Hacker"

    async def test_execute_runtime(self, mock_exec_context: ExecutionContext):
        """关键测试：测试 ExecuteRuntime 进行二次求值。"""
        runtime = ExecuteRuntime()
        
        # 初始 hp 是 100
        assert mock_exec_context.world_state["hp"] == 100
        
        # step_input 包含一个需要被二次执行的字符串
        code_str = "world['hp'] -= 25"
        result = await runtime.execute(
            step_input={"code": code_str},
            context=mock_exec_context
        )

        # 验证副作用：上下文中的 world_state 已被修改
        assert mock_exec_context.world_state["hp"] == 75
        # 验证返回值：副作用宏的返回值为 None
        assert result == {"output": None}

        # 测试带返回值的二次求值
        code_str_with_return = "f'New HP is {world.hp}'"
        result_with_return = await runtime.execute(
            step_input={"code": code_str_with_return},
            context=mock_exec_context
        )
        assert result_with_return == {"output": "New HP is 75"}