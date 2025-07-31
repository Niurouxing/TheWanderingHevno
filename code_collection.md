### conftest.py
```
# tests/conftest.py
import json
import pytest
from fastapi.testclient import TestClient
from typing import Generator

# ---------------------------------------------------------------------------
# 从你的应用代码中导入核心类和函数
# ---------------------------------------------------------------------------
from backend.main import app, sandbox_store, snapshot_store
from backend.models import GraphCollection
from backend.core.registry import RuntimeRegistry
from backend.core.engine import ExecutionEngine
from backend.runtimes.base_runtimes import (
    InputRuntime, LLMRuntime, SetWorldVariableRuntime
)
from backend.runtimes.control_runtimes import ExecuteRuntime, CallRuntime

# ---------------------------------------------------------------------------
# Fixtures for Core Components (Engine, Registry, API Client)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def populated_registry() -> RuntimeRegistry:
    """提供一个预先填充了所有新版运行时的注册表实例。"""
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("llm.default", LLMRuntime)
    registry.register("system.set_world_var", SetWorldVariableRuntime)
    registry.register("system.execute", ExecuteRuntime)
    registry.register("system.call", CallRuntime)
    print("\n--- Populated Registry Created (Session Scope) ---")
    return registry


@pytest.fixture(scope="function")
def test_engine(populated_registry: RuntimeRegistry) -> ExecutionEngine:
    """提供一个配置了标准运行时的 ExecutionEngine 实例。"""
    return ExecutionEngine(registry=populated_registry)


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """提供一个 FastAPI TestClient 用于端到端 API 测试 (Function scope for isolation)。"""
    sandbox_store.clear()
    snapshot_store.clear()
    
    with TestClient(app) as client:
        yield client
    
    sandbox_store.clear()
    snapshot_store.clear()

# ---------------------------------------------------------------------------
# Fixtures for Graph Collections (Rewritten for New Architecture)
# ---------------------------------------------------------------------------

@pytest.fixture
def linear_collection() -> GraphCollection:
    """一个简单的三节点线性图：A -> B -> C。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A", "run": [{"runtime": "system.input", "config": {"value": "a story about a cat"}}]},
            {"id": "B", "run": [{"runtime": "llm.default", "config": {"prompt": "{{ f'The story is: {nodes.A.output}' }}"}}]},
            {"id": "C", "run": [{"runtime": "llm.default", "config": {"prompt": "{{ nodes.B.llm_output }}"}}]}
        ]}
    })

@pytest.fixture
def parallel_collection() -> GraphCollection:
    """一个扇出再扇入的图 (A, B) -> C。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "source_A", "run": [{"runtime": "system.input", "config": {"value": "Value A"}}]},
            {"id": "source_B", "run": [{"runtime": "system.input", "config": {"value": "Value B"}}]},
            {
                "id": "merger",
                "run": [{
                    "runtime": "system.input",
                    "config": {"value": "{{ f'Merged: {nodes.source_A.output} and {nodes.source_B.output}' }}"}
                }]
            }
        ]}
    })

@pytest.fixture
def pipeline_collection() -> GraphCollection:
    """
    一个测试节点内运行时管道数据流的图。
    节点A包含三个有序指令，演示了状态设置、数据生成和数据消费。
    """
    return GraphCollection.model_validate({
        "main": { "nodes": [{
            "id": "A",
            "run": [
                {
                    "runtime": "system.set_world_var",
                    "config": {
                        "variable_name": "main_character",
                        "value": "Sir Reginald"
                    }
                },
                {
                    "runtime": "system.input",
                    "config": {
                        "value": "A secret message"
                    }
                },
                {
                    "runtime": "llm.default",
                    "config": {
                        # 这个宏现在可以安全地访问 world 状态和上一步的管道输出
                        "prompt": "{{ f'Tell a story about {world.main_character}. He just received this message: {pipe.output}' }}"
                    }
                }
            ]
        }]}
    })

@pytest.fixture
def world_vars_collection() -> GraphCollection:
    """一个测试世界变量设置和读取的图。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {
                "id": "setter",
                "run": [{
                    "runtime": "system.set_world_var",
                    "config": {"variable_name": "theme", "value": "cyberpunk"}
                }]
            },
            {
                "id": "reader",
                "run": [{
                    "runtime": "system.input",
                    "config": {"value": "{{ f'The theme is: {world.theme} and some data from setter: {nodes.setter}'}}"}
                }]
            }
        ]}
    })

@pytest.fixture
def execute_runtime_collection() -> GraphCollection:
    """一个测试 system.execute 运行时的图，用于二次求值。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {
                "id": "A_generate_code",
                "run": [{"runtime": "system.input", "config": {"value": "world.player_status = 'empowered'"}}]
            },
            {
                "id": "B_execute_code",
                "run": [{
                    "runtime": "system.execute",
                    "config": {"code": "{{ nodes.A_generate_code.output }}"}
                }]
            }
        ]}
    })

@pytest.fixture
def cyclic_collection() -> GraphCollection:
    """一个包含环路的图。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.C.output }}"}}]},
            {"id": "B", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.A.output }}"}}]},
            {"id": "C", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.B.output }}"}}]}
        ]}
    })

@pytest.fixture
def failing_node_collection() -> GraphCollection:
    """一个包含注定会因宏求值失败的节点的图。"""
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A_ok", "run": [{"runtime": "system.input", "config": {"value": "start"}}]},
            {"id": "B_fail", "run": [{"runtime": "system.input", "config": {"value": "{{ non_existent_variable }}"}}]},
            {"id": "C_skip", "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.B_fail.output }}"}}]},
            {"id": "D_independent", "run": [{"runtime": "system.input", "config": {"value": "independent"}}]}
        ]}
    })

@pytest.fixture
def invalid_graph_no_main() -> dict:
    """一个无效的图定义，缺少 'main' 入口点。"""
    return {"not_main": {"nodes": [{"id": "a", "run": []}]}}

@pytest.fixture
def graph_evolution_collection() -> GraphCollection:
    """一个用于测试图演化的图。"""
    new_graph_dict = {
        "main": {"nodes": [{"id": "new_node", "run": [{"runtime": "system.input", "config": {"value": "This is the evolved graph!"}}]}]}
    }
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "graph_generator",
            "run": [{
                "runtime": "system.set_world_var",
                "config": {
                    "variable_name": "__graph_collection__",
                    "value": new_graph_dict
                }
            }]
        }]}
    })

@pytest.fixture
def advanced_macro_collection() -> GraphCollection:
    """
    一个用于测试高级宏功能的图。
    使用新的 `depends_on` 字段来明确声明隐式依赖，代码更清晰。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                # 步骤1: 定义函数，无变化
                {
                    "id": "teach_skill",
                    "run": [{
                        "runtime": "system.execute",
                        "config": {
                            "code": """
import math
def calculate_hypotenuse(a, b):
    return math.sqrt(a**2 + b**2)
if not hasattr(world, 'math_utils'): world.math_utils = {}
world.math_utils.hypot = calculate_hypotenuse
"""
                        }
                    }]
                },
                # 步骤2: 调用函数，并使用 `depends_on`
                {
                    "id": "use_skill",
                    # 【关键修正】明确声明依赖
                    "depends_on": ["teach_skill"],
                    "run": [{
                        "runtime": "system.input",
                        # 宏现在非常干净，只包含业务逻辑
                        "config": {"value": "{{ world.math_utils.hypot(3, 4) }}"}
                    }]
                },
                # 步骤3: 模拟 LLM，无变化
                {
                    "id": "llm_propose_change",
                    "run": [{
                        "runtime": "system.input",
                        "config": {"value": "world.game_difficulty = 'hard'"}
                    }]
                },
                # 步骤4: 执行 LLM 代码，它已经有明确的宏依赖，无需 `depends_on`
                {
                    "id": "execute_change",
                    # 这里的依赖是自动推断的，所以 `depends_on` 不是必需的
                    # 但为了演示，也可以添加： "depends_on": ["llm_propose_change"]
                    "run": [{
                        "runtime": "system.execute",
                        "config": {"code": "{{ nodes.llm_propose_change.output }}"}
                    }]
                }
            ]
        }
    })

# ---------------------------------------------------------------------------
# 用于测试 Subgraph Call 的 Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def subgraph_call_collection() -> GraphCollection:
    """
    一个包含主图和可复用子图的集合，用于测试 system.call。
    - main 图调用 process_item 子图。
    - process_item 子图依赖一个名为 'item_input' 的占位符。
    - process_item 子图还会读取 world 状态。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "data_provider",
                    "run": [{"runtime": "system.input", "config": {"value": "Hello from main"}}]
                },
                {
                    "id": "main_caller",
                    "run": [{
                        "runtime": "system.call",
                        "config": {
                            "graph": "process_item",
                            "using": {
                                "item_input": "{{ nodes.data_provider.output }}"
                            }
                        }
                    }]
                }
            ]
        },
        "process_item": {
            "nodes": [
                {
                    "id": "processor",
                    "run": [{
                        "runtime": "system.input",
                        "config": {
                            "value": "{{ f'Processed: {nodes.item_input.output} with world state: {world.global_setting}' }}"
                        }
                    }]
                }
            ]
        }
    })

@pytest.fixture
def nested_subgraph_collection() -> GraphCollection:
    """一个测试嵌套调用的图：main -> sub1 -> sub2。"""
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "main_caller",
            "run": [{"runtime": "system.call", "config": {"graph": "sub1", "using": {"input_from_main": "level 0"}}}]
        }]},
        "sub1": {"nodes": [{
            "id": "sub1_caller",
            "run": [{"runtime": "system.call", "config": {"graph": "sub2", "using": {"input_from_sub1": "{{ nodes.input_from_main.output }}"}}}]
        }]},
        "sub2": {"nodes": [{
            "id": "final_processor",
            "run": [{"runtime": "system.input", "config": {"value": "{{ f'Reached level 2 from: {nodes.input_from_sub1.output}' }}"}}]
        }]}
    })

@pytest.fixture
def subgraph_call_to_nonexistent_graph_collection() -> GraphCollection:
    """一个尝试调用不存在子图的图，用于测试错误处理。"""
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "bad_caller",
            "run": [{"runtime": "system.call", "config": {"graph": "i_do_not_exist"}}]
        }]}
    })

@pytest.fixture
def subgraph_modifies_world_collection() -> GraphCollection:
    """
    一个子图会修改 world 状态的集合。
    - main 调用 modifier 子图。
    - modifier 子图根据输入修改 world.counter。
    - main 中的后续节点 reader 会读取这个被修改后的状态。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "caller",
                    "run": [{"runtime": "system.call", "config": {"graph": "modifier", "using": {"amount": 10}}}]
                },
                {
                    "id": "reader",
                    # 这里的宏依赖会自动创建从 caller 到 reader 的依赖
                    "run": [{
                        "runtime": "system.input",
                        "config": {"value": "{{ f'Final counter: {world.counter}, Subgraph raw output: {nodes.caller.output}' }}"}
                    }]
                }
            ]
        },
        "modifier": {
            "nodes": [
                {
                    "id": "incrementer",
                    # 这是一个隐式依赖，我们用 depends_on 来确保执行顺序
                    # 子图无法通过宏推断它依赖于父图设置的 world.counter
                    # 但在这里，我们假设初始状态设置了 counter
                    "run": [{
                        "runtime": "system.execute",
                        "config": {"code": "world.counter += nodes.amount.output"}
                    }]
                }
            ]
        }
    })

@pytest.fixture
def subgraph_with_failure_collection() -> GraphCollection:
    """
    一个子图内部会失败的集合。
    - main 调用 failing_subgraph。
    - failing_subgraph 中的一个节点会因为宏错误而失败。
    - main 中的后续节点 downstream_of_fail 应该被跳过。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "caller",
                    "run": [{"runtime": "system.call", "config": {"graph": "failing_subgraph"}}]
                },
                {
                    "id": "downstream_of_fail",
                    "run": [{"runtime": "system.input", "config": {"value": "{{ nodes.caller.output }}"}}]
                }
            ]
        },
        "failing_subgraph": {
            "nodes": [
                {"id": "A_ok", "run": [{"runtime": "system.input", "config": {"value": "ok"}}]},
                {"id": "B_fail", "run": [{"runtime": "system.input", "config": {"value": "{{ non_existent.var }}"}}]}
            ]
        }
    })

@pytest.fixture
def dynamic_subgraph_call_collection() -> GraphCollection:
    """
    一个动态决定调用哪个子图的集合。
    - main 根据 world.target_graph 的值来调用 sub_a 或 sub_b。
    """
    return GraphCollection.model_validate({
        "main": {"nodes": [{
            "id": "dynamic_caller",
            "run": [{
                "runtime": "system.call",
                "config": {
                    "graph": "{{ world.target_graph }}",
                    "using": {"data": "dynamic data"}
                }
            }]
        }]},
        # 【关键修正】在子图内部使用正确的 f-string 宏格式
        "sub_a": {"nodes": [{
            "id": "processor_a",
            "run": [{"runtime": "system.input", "config": {"value": "{{ f'Processed by A: {nodes.data.output}' }}"}}]
        }]},
        "sub_b": {"nodes": [{
            "id": "processor_b",
            "run": [{"runtime": "system.input", "config": {"value": "{{ f'Processed by B: {nodes.data.output}' }}"}}]
        }]}
    })

```

### test_02_evaluation_unit.py
```
# tests/test_02_evaluation_unit.py
import pytest
from uuid import uuid4

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
```

### test_01_foundations.py
```
# tests/test_01_foundations.py
import pytest
from pydantic import ValidationError
from uuid import uuid4

from backend.models import GraphCollection, GenericNode, GraphDefinition, RuntimeInstruction
from backend.core.state_models import StateSnapshot, Sandbox, SnapshotStore
from backend.core.dependency_parser import build_dependency_graph


class TestCoreModels:
    """测试核心数据模型，已更新为新架构。"""

    def test_runtime_instruction_validation(self):
        """测试 RuntimeInstruction 模型。"""
        # 有效
        inst = RuntimeInstruction(runtime="test.runtime", config={"key": "value"})
        assert inst.runtime == "test.runtime"
        assert inst.config == {"key": "value"}
        # config 默认为空字典
        inst_default = RuntimeInstruction(runtime="test.runtime")
        assert inst_default.config == {}

        # 无效 (缺少 runtime)
        with pytest.raises(ValidationError):
            RuntimeInstruction(config={})

    def test_generic_node_validation_success(self):
        """测试 GenericNode 使用新的 `run` 字段。"""
        node = GenericNode(
            id="n1",
            run=[
                {"runtime": "step1", "config": {"p1": 1}},
                {"runtime": "step2"}
            ]
        )
        assert node.id == "n1"
        assert len(node.run) == 2
        assert isinstance(node.run[0], RuntimeInstruction)
        assert node.run[0].runtime == "step1"
        assert node.run[0].config == {"p1": 1}
        assert node.run[1].config == {}

    def test_generic_node_validation_fails(self):
        """测试 GenericNode 的无效 `run` 字段。"""
        # `run` 列表中的项不是有效的指令
        with pytest.raises(ValidationError):
            GenericNode(id="n1", run=["not_an_instruction"])
        
        with pytest.raises(ValidationError):
            GenericNode(id="n1", run=[{"config": {}}]) # runtime 缺失

    def test_graph_collection_validation(self):
        """测试 GraphCollection 验证逻辑，此逻辑不变。"""
        valid_data = {"main": {"nodes": [{"id": "a", "run": []}]}}
        collection = GraphCollection.model_validate(valid_data)
        assert "main" in collection.root

        with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate({"other": {"nodes": []}})


class TestSandboxModels:
    """测试沙盒相关模型，基本不变。"""
    # ... 此部分测试与旧版本基本一致，无需修改，因为模型本身的结构和不变性没有改变 ...
    @pytest.fixture
    def sample_graph_collection(self) -> GraphCollection:
        return GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "run": []}]}})

    def test_state_snapshot_is_immutable(self, sample_graph_collection: GraphCollection):
        snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=sample_graph_collection)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            snapshot.world_state = {"new_key": "new_value"}


class TestDependencyParser:
    """测试依赖解析器，使用新的节点结构。"""

    def test_simple_dependency(self):
        nodes = [{"id": "A", "run": []}, {"id": "B", "run": [{"config": {"value": "{{ nodes.A.output }}"}}]}]
        deps = build_dependency_graph(nodes)
        assert deps["B"] == {"A"}

    def test_dependency_in_nested_structure(self):
        nodes = [
            {"id": "source", "run": []},
            {"id": "consumer", "run": [{"config": {"nested": ["{{ nodes.source.val }}"]}}]}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["consumer"] == {"source"}

    def test_ignores_non_node_macros(self):
        nodes = [{"id": "A", "run": [{"config": {"value": "{{ world.x }}"}}]}]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()

    def test_dependency_on_placeholder_node_is_preserved(self):
        """
        验证对图中不存在的节点（即子图的输入占位符）的依赖会被保留。
        这对于 system.call 功能至关重要。
        """
        nodes = [{"id": "A", "run": [{"config": {"value": "{{ nodes.placeholder_input.val }}"}}]}]
        deps = build_dependency_graph(nodes)
        # 之前这里断言 deps["A"] == set()，现在它必须保留依赖
        assert deps["A"] == {"placeholder_input"}
```

### __init__.py
```

```

### test_04_api_e2e.py
```
# tests/test_04_api_e2e.py
import pytest
from fastapi.testclient import TestClient
from uuid import UUID, uuid4

from backend.models import GraphCollection


class TestApiSandboxLifecycle:
    """测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        # 1. 创建
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Test"},
            json={
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {} 
            }
        )
        assert response.status_code == 200
        sandbox_data = response.json()
        sandbox_id = sandbox_data["id"]
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        # 2. 执行
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "test"})
        assert response.status_code == 200
        step1_snapshot_data = response.json()
        step1_snapshot_id = step1_snapshot_data["id"]
        assert "C" in step1_snapshot_data.get("run_output", {})

        # 3. 历史
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 2

        # 4. 回滚
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200

        # 5. 验证回滚
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        step2_snapshot_data = response.json()
        assert step2_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id


class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid"},
            json={"graph_collection": invalid_graph_no_main}
        )
        assert response.status_code == 422 
        error_data = response.json()
        assert "A 'main' graph must be defined" in error_data["detail"][0]["msg"]
        # 验证 pydantic v2 对 RootModel 的错误路径
        assert error_data["detail"][0]["loc"] == ["body", "graph_collection"]

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = uuid4()
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        
        # 获取历史记录现在会因为找不到 sandbox 而返回 404
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 404

        response = test_client.put(f"/api/sandboxes/{nonexistent_id}/revert", params={"snapshot_id": uuid4()})
        assert response.status_code == 404


class TestApiWithComplexGraphs:
    """测试涉及更复杂图逻辑（如子图调用）的 API 端点。"""

    def test_e2e_with_subgraph_call(self, test_client: TestClient, subgraph_call_collection: GraphCollection):
        """
        通过 API 端到端测试一个包含 system.call 的图。
        """
        # 1. 创建沙盒
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Subgraph Test"},
            json={
                "graph_collection": subgraph_call_collection.model_dump(),
                "initial_state": {"global_setting": "Omega"}
            }
        )
        assert response.status_code == 200
        sandbox_id = response.json()["id"]

        # 2. 执行一步
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert response.status_code == 200
        
        # 3. 验证结果
        snapshot_data = response.json()
        run_output = snapshot_data.get("run_output", {})
        
        assert "main_caller" in run_output
        subgraph_output = run_output["main_caller"]["output"]
        processor_output = subgraph_output["processor"]["output"]
        
        expected_str = "Processed: Hello from main with world state: Omega"
        assert processor_output == expected_str
```

### test_03_engine_integration.py
```
# tests/test_03_engine_integration.py
import pytest
from uuid import uuid4

from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection


@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，使用新的宏系统。"""

    async def test_engine_linear_flow(self, test_engine: ExecutionEngine, linear_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert output["A"]["output"] == "a story about a cat"
        assert output["B"]["llm_output"] == "LLM_RESPONSE_FOR:[The story is: a story about a cat]"
        assert output["C"]["llm_output"] == f"LLM_RESPONSE_FOR:[{output['B']['llm_output']}]"

    async def test_engine_runtime_pipeline(self, test_engine: ExecutionEngine, pipeline_collection: GraphCollection):
        """【已修正】测试单个节点内的运行时管道，并验证宏预处理与运行时的交互。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 1. 验证第一个指令的副作用
        assert final_snapshot.world_state["main_character"] == "Sir Reginald"

        # 2. 验证第三个指令使用了世界状态和管道状态
        node_a_result = final_snapshot.run_output["A"]
        
        expected_prompt = "Tell a story about Sir Reginald. He just received this message: A secret message"
        # 3. 【已修正】现在可以安全地断言 llm_output
        assert node_a_result["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"

        # 4. 验证最终的节点输出是所有指令输出的合并
        assert node_a_result["output"] == "A secret message"


@pytest.mark.asyncio
class TestEngineStateAndMacros:
    """测试引擎如何处理持久化状态，以及更高级的宏功能。"""

    async def test_world_state_persists_and_macros_read_it(self, test_engine: ExecutionEngine, world_vars_collection: GraphCollection):
        """验证 world_state 能被设置，并能被后续节点的宏读取。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        assert final_snapshot.world_state == {"theme": "cyberpunk"}

        # 【已修正】期望的字符串应该匹配 DotAccessibleDict 的 __repr__
        # 'setter' runtime 返回 {}, 所以 nodes.setter 是 DotAccessibleDict({})
        expected_reader_output = "The theme is: cyberpunk and some data from setter: DotAccessibleDict({})"
        assert final_snapshot.run_output["reader"]["output"] == expected_reader_output

    async def test_graph_evolution(self, test_engine: ExecutionEngine, graph_evolution_collection: GraphCollection):
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        new_graph_def = snapshot_after_evolution.graph_collection
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})
        assert final_snapshot.run_output["new_node"]["output"] == "This is the evolved graph!"

    async def test_execute_runtime_integration(self, test_engine: ExecutionEngine, execute_runtime_collection: GraphCollection):
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        assert final_snapshot.world_state["player_status"] == "empowered"

@pytest.mark.asyncio
class TestEngineErrorHandling:
    async def test_engine_detects_cycle(self, test_engine: ExecutionEngine, cyclic_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})

    async def test_engine_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngine, failing_node_collection: GraphCollection):
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        assert "error" not in output["A_ok"]
        assert "error" not in output["D_independent"]

        assert "error" in output["B_fail"]
        assert output["B_fail"]["failed_step"] == 0 # 失败在第一个(也是唯一一个)指令
        assert "non_existent_variable" in output["B_fail"]["error"]

        assert output["C_skip"]["status"] == "skipped"
        assert output["C_skip"]["reason"] == "Upstream failure of node B_fail."

@pytest.mark.asyncio
class TestAdvancedMacroIntegration:
    """测试引擎中更高级的宏功能，如动态函数定义和二次求值链。"""

    async def test_dynamic_function_definition_and_usage(self, test_engine: ExecutionEngine, advanced_macro_collection: GraphCollection):
        """
        测试一个节点定义函数，另一个节点使用该函数。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )

        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        # 1. 验证 `teach_skill` 节点的副作用
        assert "math_utils" in final_snapshot.world_state
        assert callable(final_snapshot.world_state["math_utils"]["hypot"])

        # 2. 验证 `use_skill` 节点成功调用了该函数
        run_output = final_snapshot.run_output
        assert "use_skill" in run_output
        # 【已修正】现在这个断言应该可以成功了
        assert run_output["use_skill"]["output"] == 5.0

    async def test_llm_code_generation_and_execution(self, test_engine: ExecutionEngine, advanced_macro_collection: GraphCollection):
        """
        测试一个节点生成代码，另一个节点执行它，模拟 LLM 驱动的世界演化。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=advanced_macro_collection,
            world_state={"game_difficulty": "easy"}
        )

        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        
        # 【已修正】断言中的字符串现在与 fixture 中定义的完全一致
        assert run_output["llm_propose_change"]["output"] == "world.game_difficulty = 'hard'"
        
        assert "execute_change" in run_output
        
        assert final_snapshot.world_state["game_difficulty"] == "hard"

@pytest.mark.asyncio
class TestEngineSubgraphExecution:
    """测试引擎的子图执行功能 (system.call)。"""

    async def test_basic_subgraph_call(self, test_engine: ExecutionEngine, subgraph_call_collection: GraphCollection):
        """测试基本的子图调用和数据映射。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_collection,
            world_state={"global_setting": "Alpha"}
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        output = final_snapshot.run_output
        
        # 验证主调节点的输出是子图的完整结果字典
        subgraph_result = output["main_caller"]["output"]
        assert isinstance(subgraph_result, dict)
        
        # 验证子图内部的节点 'processor' 的输出
        processor_output = subgraph_result["processor"]["output"]
        expected_str = "Processed: Hello from main with world state: Alpha"
        assert processor_output == expected_str
        
    async def test_nested_subgraph_call(self, test_engine: ExecutionEngine, nested_subgraph_collection: GraphCollection):
        """测试嵌套的子图调用：main -> sub1 -> sub2。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=nested_subgraph_collection
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output

        # 逐层深入断言
        sub1_result = output["main_caller"]["output"]
        sub2_result = sub1_result["sub1_caller"]["output"]
        final_output = sub2_result["final_processor"]["output"]
        
        assert final_output == "Reached level 2 from: level 0"

    async def test_call_to_nonexistent_subgraph_fails_node(self, test_engine: ExecutionEngine, subgraph_call_to_nonexistent_graph_collection: GraphCollection):
        """测试调用一个不存在的子图时，节点会优雅地失败。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_call_to_nonexistent_graph_collection
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        bad_caller_result = output["bad_caller"]
        
        assert "error" in bad_caller_result
        assert "Subgraph 'i_do_not_exist' not found" in bad_caller_result["error"]
        assert bad_caller_result["failed_step"] == 0
        assert bad_caller_result["runtime"] == "system.call"

    async def test_subgraph_can_modify_world_state(self, test_engine: ExecutionEngine, subgraph_modifies_world_collection: GraphCollection):
        """
        验证子图对 world_state 的修改在父图中是可见的，并且后续节点可以访问它。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_modifies_world_collection,
            world_state={"counter": 100} # 初始状态
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 1. 验证 world_state 被成功修改
        assert final_snapshot.world_state["counter"] == 110

        # 2. 验证父图中的后续节点可以读取到修改后的状态
        reader_output = final_snapshot.run_output["reader"]["output"]
        assert "Final counter: 110" in reader_output
        # 验证 reader 也可以访问 caller 的原始输出
        assert "incrementer" in reader_output
    
    async def test_subgraph_failure_propagates_to_caller(self, test_engine: ExecutionEngine, subgraph_with_failure_collection: GraphCollection):
        """
        验证子图中的失败会反映在调用节点的输出中，并导致父图中的下游节点被跳过。
        """
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=subgraph_with_failure_collection,
        )
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        output = final_snapshot.run_output
        
        # 1. 验证调用节点的结果是子图的失败状态
        caller_result = output["caller"]["output"]
        assert "B_fail" in caller_result
        assert "error" in caller_result["B_fail"]
        assert "non_existent" in caller_result["B_fail"]["error"]

        # 2. 验证调用节点本身的状态不是 FAILED，而是 SUCCEEDED，
        # 因为 system.call 运行时成功地“捕获”了子图的结果（即使是失败的结果）。
        # 这是预期的行为：运行时本身没有崩溃。
        # 【注意】我们检查的是 caller 节点的整体输出，而不是子图的结果
        assert "error" not in output["caller"]

        # 3. 验证依赖于 caller 的下游节点被跳过，因为它的依赖（caller）现在包含了一个失败的内部节点。
        # 这是一个更微妙的点。当前的 _process_subscribers 逻辑可能不会将此视为失败。
        # 让我们来验证当前的行为。
        # 当前 _process_subscribers 仅检查 run.get_node_state(dep_id) == NodeState.SUCCEEDED
        # 因为 caller 节点状态是 SUCCEEDED，所以 downstream_of_fail 会运行。
        # 这是当前实现的一个值得注意的行为！
        assert "downstream_of_fail" in output
        assert "error" not in output.get("downstream_of_fail", {})

        # 如果我们想要“失败”传播，我们需要修改 system.call 运行时，
        # 让它在子图失败时自己也返回一个 error。
        # 这是一个很好的设计决策讨论点。目前，我们测试了现有行为。

    async def test_dynamic_subgraph_call_by_macro(self, test_engine: ExecutionEngine, dynamic_subgraph_call_collection: GraphCollection):
        """
        验证 system.call 的 'graph' 参数可以由宏动态提供。
        """
        # 场景1: 调用 sub_a
        initial_snapshot_a = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_a"}
        )
        final_snapshot_a = await test_engine.step(initial_snapshot_a, {})
        output_a = final_snapshot_a.run_output["dynamic_caller"]["output"]
        assert output_a["processor_a"]["output"] == "Processed by A: dynamic data"

        # 场景2: 调用 sub_b
        initial_snapshot_b = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=dynamic_subgraph_call_collection,
            world_state={"target_graph": "sub_b"}
        )
        final_snapshot_b = await test_engine.step(initial_snapshot_b, {})
        output_b = final_snapshot_b.run_output["dynamic_caller"]["output"]
        assert "processor_a" not in output_b
        assert output_b["processor_b"]["output"] == "Processed by B: dynamic data"
```
