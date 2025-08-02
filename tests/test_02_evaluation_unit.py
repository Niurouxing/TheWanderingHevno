# tests/test_02_evaluation_unit.py
import pytest
from uuid import uuid4
import asyncio

from backend.core.hooks import HookManager
from backend.core.evaluation import (
    evaluate_expression, evaluate_data, build_evaluation_context
)
from backend.core.contracts import ExecutionContext, StateSnapshot
from backend.core.state import create_main_execution_context # <-- 导入工厂函数
from backend.core.models import GraphCollection
from backend.runtimes.base_runtimes import SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime
from backend.llm.service import MockLLMService
from backend.core.hooks import HookManager

@pytest.fixture
def mock_exec_context(hook_manager: HookManager) -> ExecutionContext:
    """提供一个可复用的、模拟的 ExecutionContext。"""
    graph_coll = GraphCollection.model_validate({"main": {"nodes": []}})
    initial_world = {"user_name": "Alice", "hp": 100}
    snapshot = StateSnapshot(
        sandbox_id=uuid4(),
        graph_collection=graph_coll,
        world_state=initial_world
    )
    
    # 【核心修复】直接调用从 state.py 导入的工厂函数
    context = create_main_execution_context(
        snapshot=snapshot, 
        services={"llm": MockLLMService()},
        hook_manager=hook_manager
    )
    
    # 后续的上下文设置保持不变
    context.node_states = {"node_A": {"output": "Success"}}
    context.run_vars = {"trigger_input": {"message": "Do it!"}}

    return context

@pytest.fixture
def mock_eval_context(mock_exec_context: ExecutionContext) -> dict:
    """提供一个扁平化的、用于宏执行的字典上下文。"""
    return build_evaluation_context(mock_exec_context, pipe_vars={"from_pipe": "pipe_data"})

@pytest.fixture
def test_lock() -> asyncio.Lock:
    """提供一个在测试中共享的锁。"""
    return asyncio.Lock()

@pytest.mark.asyncio
class TestEvaluationCore:
    """对宏求值核心 `evaluate_expression` 进行深度单元测试。"""
    
    async def test_simple_expressions(self, mock_eval_context, test_lock):
        assert await evaluate_expression("1 + 1", mock_eval_context, test_lock) == 2

    async def test_context_access(self, mock_eval_context, test_lock):
        code = "f'{nodes.node_A.output}, {world.user_name}, {run.trigger_input.message}, {pipe.from_pipe}'"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == "Success, Alice, Do it!, pipe_data"

    async def test_side_effects_on_world_state(self, mock_exec_context: ExecutionContext, test_lock):
        eval_context = build_evaluation_context(mock_exec_context)
        assert eval_context["world"].hp == 100
        await evaluate_expression("world.hp -= 10", eval_context, test_lock)
        assert eval_context["world"].hp == 90
        # 验证底层共享状态是否真的被修改
        assert mock_exec_context.shared.world_state["hp"] == 90

    async def test_multiline_script_with_return(self, mock_eval_context, test_lock):
        code = """
bonus = 0
if world.hp > 50:
    bonus = 20
else:
    bonus = 5
bonus
"""
        # 测试 if 分支
        mock_eval_context["world"].hp = 80
        assert await evaluate_expression(code, mock_eval_context, test_lock) == 20
        # 测试 else 分支
        mock_eval_context["world"].hp = 40
        assert await evaluate_expression(code, mock_eval_context, test_lock) == 5

    async def test_syntax_error_handling(self, mock_eval_context, test_lock):
        with pytest.raises(ValueError, match="Macro syntax error"):
            await evaluate_expression("1 +", mock_eval_context, test_lock)

@pytest.mark.asyncio
class TestRecursiveEvaluation:
    """对递归求值函数 `evaluate_data` 进行测试。"""
    
    async def test_evaluate_data_recursively(self, mock_eval_context, test_lock):
        data = {
            "static": "hello",
            "direct": "{{ 1 + 2 }}",
            "nested": ["{{ world.user_name }}", {"deep": "{{ pipe.from_pipe.upper() }}"}]
        }
        result = await evaluate_data(data, mock_eval_context, test_lock)
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
        assert "new_var" not in mock_exec_context.shared.world_state
        await runtime.execute(
            config={"variable_name": "new_var", "value": "is_set"},
            context=mock_exec_context
        )
        assert mock_exec_context.shared.world_state["new_var"] == "is_set"

    async def test_execute_runtime(self, mock_exec_context: ExecutionContext):
        runtime = ExecuteRuntime()
        assert mock_exec_context.shared.world_state["hp"] == 100
        code_str = "world.hp -= 25"
        

        await runtime.execute(
            config={"code": code_str}, 
            context=mock_exec_context
        )
        assert mock_exec_context.shared.world_state["hp"] == 75

        code_str_with_return = "f'New HP is {world.hp}'"
        result = await runtime.execute(
            config={"code": code_str_with_return}, 
            context=mock_exec_context
        )
        assert result == {"output": "New HP is 75"}


@pytest.mark.asyncio
class TestBuiltinModules:
    
    async def test_random_module(self, mock_eval_context, test_lock):
        result = await evaluate_expression("random.randint(10, 10)", mock_eval_context, test_lock)
        assert result == 10

    async def test_math_module(self, mock_eval_context, test_lock):
        result = await evaluate_expression("math.ceil(3.14)", mock_eval_context, test_lock)
        assert result == 4

    async def test_json_module(self, mock_eval_context, test_lock):
        code = "json.dumps({'a': 1})" # `import json` is not needed due to pre-imported modules
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == '{"a": 1}'

    async def test_re_module(self, mock_eval_context, test_lock):
        code = "re.match(r'\\w+', 'hello').group(0)"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == "hello"

@pytest.mark.asyncio
class TestDotAccessibleDictInteraction:
    
    async def test_deep_read(self, mock_exec_context, test_lock):
        mock_exec_context.shared.world_state["player"] = {"stats": {"strength": 10}}
        eval_context = build_evaluation_context(mock_exec_context)
        result = await evaluate_expression("world.player.stats.strength", eval_context, test_lock)
        assert result == 10

    async def test_deep_write(self, mock_exec_context, test_lock):
        mock_exec_context.shared.world_state["player"] = {"stats": {"strength": 10}}
        eval_context = build_evaluation_context(mock_exec_context)
        await evaluate_expression("world.player.stats.strength = 15", eval_context, test_lock)
        assert mock_exec_context.shared.world_state["player"]["stats"]["strength"] == 15
    
    async def test_attribute_error_on_missing_key(self, mock_eval_context, test_lock):
        with pytest.raises(AttributeError):
            # The evaluator will raise AttributeError when a key is not found
            await evaluate_expression("world.non_existent_key", mock_eval_context, test_lock)

    async def test_list_of_dicts_access(self, mock_exec_context, test_lock):
        mock_exec_context.shared.world_state["inventory"] = [{"name": "sword"}, {"name": "shield"}]
        eval_context = build_evaluation_context(mock_exec_context)
        result = await evaluate_expression("world.inventory[1].name", eval_context, test_lock)
        assert result == "shield"

@pytest.mark.asyncio
class TestEdgeCases:
    
    async def test_macro_returning_none(self, mock_eval_context, test_lock):
        code = "x = 1" # This script doesn't have an expression as its last line
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result is None

    async def test_empty_macro(self, mock_eval_context, test_lock):
        result = await evaluate_expression("", mock_eval_context, test_lock)
        assert result is None
        result = await evaluate_expression("   ", mock_eval_context, test_lock)
        assert result is None

    async def test_evaluate_data_with_none_values(self, mock_eval_context, test_lock):
        data = {"key1": None, "key2": "{{ 1 + 1 }}"}
        result = await evaluate_data(data, mock_eval_context, test_lock)
        assert result == {"key1": None, "key2": 2}