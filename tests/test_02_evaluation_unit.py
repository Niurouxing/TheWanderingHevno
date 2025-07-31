# tests/test_02_evaluation_unit.py
import pytest
from uuid import uuid4
import asyncio

from backend.core.evaluation import (
    evaluate_expression, evaluate_data, build_evaluation_context
)
from backend.core.types import ExecutionContext
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection
from backend.runtimes.base_runtimes import SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime

@pytest.fixture
def mock_exec_context() -> ExecutionContext:
    """提供一个可复用的、模拟的 ExecutionContext。"""
    graph_coll = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_coll)
    context = ExecutionContext.from_snapshot(snapshot)
    context.node_states = {"node_A": {"output": "Success"}}
    context.world_state = {"user_name": "Alice", "hp": 100}
    context.run_vars = {"trigger_input": {"message": "Do it!"}}

    if "global_write_lock" not in context.internal_vars:
        context.internal_vars["global_write_lock"] = asyncio.Lock()

    return context

@pytest.fixture
def mock_eval_context(mock_exec_context: ExecutionContext) -> dict:
    """提供一个扁平化的、用于宏执行的字典上下文。"""
    return build_evaluation_context(mock_exec_context, pipe_vars={"from_pipe": "pipe_data"})

@pytest.mark.asyncio
class TestEvaluationCore:
    """对宏求值核心 `evaluate_expression` 进行深度单元测试。"""
    async def test_simple_expressions(self, mock_eval_context):
        assert await evaluate_expression("1 + 1", mock_eval_context) == 2

    async def test_context_access(self, mock_eval_context):
        code = "f'{nodes.node_A.output}, {world.user_name}, {run.trigger_input.message}, {pipe.from_pipe}'"
        result = await evaluate_expression(code, mock_eval_context)
        assert result == "Success, Alice, Do it!, pipe_data"

    async def test_side_effects_on_world_state(self, mock_exec_context: ExecutionContext):
        eval_context = build_evaluation_context(mock_exec_context)
        assert eval_context["world"].hp == 100
        await evaluate_expression("world.hp -= 10", eval_context)
        assert eval_context["world"].hp == 90
        # 验证原始字典也被修改了
        assert mock_exec_context.world_state["hp"] == 90

    async def test_multiline_script_with_return(self, mock_eval_context):
        """测试多行脚本，并验证最后一行表达式作为返回值。"""
        # 【已修正】确保最后一行是一个独立的表达式，它将被作为返回值。
        code = """
x = 10
result = 0
if world.hp > 50:
    result = x * 2
else:
    result = x / 2
result
"""
        # 测试 if 分支
        mock_eval_context["world"].hp = 80
        assert await evaluate_expression(code, mock_eval_context) == 20
        
        # 测试 else 分支
        mock_eval_context["world"].hp = 40
        assert await evaluate_expression(code, mock_eval_context) == 5.0

    async def test_syntax_error_handling(self, mock_eval_context):
        with pytest.raises(ValueError, match="Macro syntax error"):
            await evaluate_expression("1 +", mock_eval_context)

@pytest.mark.asyncio
class TestRecursiveEvaluation:
    """对递归求值函数 `evaluate_data` 进行测试。"""
    async def test_evaluate_data_recursively(self, mock_eval_context):
        data = {
            "static": "hello",
            "direct": "{{ 1 + 2 }}",
            "nested": ["{{ world.user_name }}", {"deep": "{{ pipe.from_pipe.upper() }}"}]
        }
        result = await evaluate_data(data, mock_eval_context)
        expected = {
            "static": "hello",
            "direct": 3,
            "nested": ["Alice", {"deep": "PIPE_DATA"}]
        }
        assert result == expected

@pytest.mark.asyncio
class TestRuntimesWithMacros:
    """对每个运行时进行独立的单元测试，假设宏预处理已完成。"""
    async def test_set_world_variable_runtime(self, mock_exec_context: ExecutionContext):
        runtime = SetWorldVariableRuntime()
        assert "new_var" not in mock_exec_context.world_state
        # 模拟引擎调用，config 已经是宏求值后的结果。
        await runtime.execute(
            config={"variable_name": "new_var", "value": "is_set"},
            context=mock_exec_context
        )
        assert mock_exec_context.world_state["new_var"] == "is_set"

    async def test_execute_runtime(self, mock_exec_context: ExecutionContext):
        runtime = ExecuteRuntime()
        assert mock_exec_context.world_state["hp"] == 100
        code_str = "world.hp -= 25"
        await runtime.execute(config={"code": code_str}, context=mock_exec_context)
        assert mock_exec_context.world_state["hp"] == 75

        code_str_with_return = "f'New HP is {world.hp}'"
        result = await runtime.execute(config={"code": code_str_with_return}, context=mock_exec_context)
        assert result == {"output": "New HP is 75"}


@pytest.mark.asyncio
class TestBuiltinModules:
    """测试宏中预置的 Python 模块。"""

    async def test_random_module(self, mock_eval_context):
        # 验证 random 模块可用
        result = await evaluate_expression("random.randint(10, 10)", mock_eval_context)
        assert result == 10

    async def test_math_module(self, mock_eval_context):
        # 验证 math 模块可用
        result = await evaluate_expression("math.ceil(3.14)", mock_eval_context)
        assert result == 4

    async def test_json_module(self, mock_eval_context):
        # 验证 json 模块可用
        code = """
import json
json.dumps({'a': 1})
"""
        result = await evaluate_expression(code, mock_eval_context)
        assert result == '{"a": 1}'

    async def test_re_module(self, mock_eval_context):
        # 验证 re 模块可用
        code = "re.match(r'\\w+', 'hello').group(0)"
        result = await evaluate_expression(code, mock_eval_context)
        assert result == "hello"


@pytest.mark.asyncio
class TestDotAccessibleDictInteraction:
    """深入测试宏与 DotAccessibleDict 的交互。"""

    async def test_deep_read(self, mock_exec_context):
        # 添加深层嵌套数据
        mock_exec_context.world_state["player"] = {"stats": {"strength": 10}}
        eval_context = build_evaluation_context(mock_exec_context)
        
        result = await evaluate_expression("world.player.stats.strength", eval_context)
        assert result == 10

    async def test_deep_write(self, mock_exec_context):
        mock_exec_context.world_state["player"] = {"stats": {"strength": 10}}
        eval_context = build_evaluation_context(mock_exec_context)

        # 通过宏进行深层写入
        await evaluate_expression("world.player.stats.strength = 15", eval_context)

        # 验证原始字典已被修改
        assert mock_exec_context.world_state["player"]["stats"]["strength"] == 15
    
    async def test_attribute_error_on_missing_key(self, mock_eval_context):
        # 测试访问不存在的键会引发 AttributeError
        with pytest.raises(AttributeError, match="'DotAccessibleDict' object has no attribute 'non_existent_key'"):
            await evaluate_expression("world.non_existent_key", mock_eval_context)

    async def test_list_of_dicts_access(self, mock_exec_context):
        mock_exec_context.world_state["inventory"] = [{"name": "sword"}, {"name": "shield"}]
        eval_context = build_evaluation_context(mock_exec_context)

        # 验证可以访问列表中的字典的属性
        result = await evaluate_expression("world.inventory[1].name", eval_context)
        assert result == "shield"


@pytest.mark.asyncio
class TestEdgeCases:
    """测试宏系统的边界情况。"""

    async def test_macro_returning_none(self, mock_eval_context):
        # 宏执行了一个没有返回值的操作
        code = "x = 1"
        result = await evaluate_expression(code, mock_eval_context)
        assert result is None

    async def test_empty_macro(self, mock_eval_context):
        # 空宏应该返回 None
        result = await evaluate_expression("", mock_eval_context)
        assert result is None
        
        result = await evaluate_expression("   ", mock_eval_context)
        assert result is None

    async def test_evaluate_data_with_none_values(self, mock_eval_context):
        # 验证 evaluate_data 能正确处理包含 None 的数据结构
        data = {"key1": None, "key2": "{{ 1 + 1 }}"}
        result = await evaluate_data(data, mock_eval_context)
        assert result == {"key1": None, "key2": 2}