# plugins/core_engine/tests/test_evaluation.py

import pytest
import asyncio
from uuid import uuid4


from backend.container import Container
from backend.core.contracts import ExecutionContext, StateSnapshot, GraphCollection
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.evaluation import evaluate_expression, evaluate_data, build_evaluation_context
from plugins.core_engine.state import create_main_execution_context
from plugins.core_engine.runtimes.base_runtimes import SetWorldVariableRuntime

# 从依赖插件导入
from plugins.core_llm.service import MockLLMService

@pytest.fixture
def mock_exec_context() -> ExecutionContext:
    """提供一个可复用的、模拟的 ExecutionContext。"""
    container = Container()
    container.register("llm_service", lambda: MockLLMService())
    
    graph_coll = GraphCollection.model_validate({"main": {"nodes": []}})
    snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_coll, world_state={"user_name": "Alice", "hp": 100})
    
    context = create_main_execution_context(
        snapshot=snapshot, 
        container=container,
        hook_manager=HookManager()
    )
    context.node_states = {"node_A": {"output": "Success"}}
    context.run_vars = {"trigger_input": {"message": "Do it!"}}
    return context

@pytest.fixture
def mock_eval_context(mock_exec_context: ExecutionContext) -> dict:
    return build_evaluation_context(mock_exec_context, pipe_vars={"from_pipe": "pipe_data"})

@pytest.fixture
def test_lock() -> asyncio.Lock:
    return asyncio.Lock()

@pytest.mark.asyncio
class TestEvaluationUnit:
    """对宏求值核心 `evaluate_expression` 和 `evaluate_data` 进行单元测试。"""
    
    async def test_context_access(self, mock_eval_context, test_lock):
        code = "f'{nodes.node_A.output}, {world.user_name}, {run.trigger_input.message}, {pipe.from_pipe}'"
        result = await evaluate_expression(code, mock_eval_context, test_lock)
        assert result == "Success, Alice, Do it!, pipe_data"

    async def test_side_effects_on_world_state(self, mock_exec_context: ExecutionContext, test_lock):
        eval_context = build_evaluation_context(mock_exec_context)
        await evaluate_expression("world.hp -= 10", eval_context, test_lock)
        assert mock_exec_context.shared.world_state["hp"] == 90

    async def test_evaluate_data_recursively(self, mock_eval_context, test_lock):
        data = {"direct": "{{ 1 + 2 }}", "nested": ["{{ world.user_name }}"]}
        result = await evaluate_data(data, mock_eval_context, test_lock)
        assert result == {"direct": 3, "nested": ["Alice"]}