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
# --- 导入新的和更新后的运行时 ---
from backend.runtimes.base_runtimes import (
    InputRuntime, LLMRuntime, SetWorldVariableRuntime
)
from backend.runtimes.control_runtimes import ExecuteRuntime

# ---------------------------------------------------------------------------
# Fixtures for Core Components (Engine, Registry, API Client)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def populated_registry() -> RuntimeRegistry:
    """
    提供一个预先填充了所有【新版】运行时的注册表实例。
    - 移除了 TemplateRuntime
    - 新增了 ExecuteRuntime
    """
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("llm.default", LLMRuntime)
    registry.register("system.set_world_var", SetWorldVariableRuntime)
    registry.register("system.execute", ExecuteRuntime)
    # 当添加 map/call 运行时后，在这里注册它们
    # registry.register("system.map", MapRuntime)
    # registry.register("system.call", CallRuntime)
    print("\n--- Populated Registry Created (Session Scope) ---")
    return registry


@pytest.fixture(scope="function")
def test_engine(populated_registry: RuntimeRegistry) -> ExecutionEngine:
    """提供一个配置了标准运行时的 ExecutionEngine 实例。"""
    return ExecutionEngine(registry=populated_registry)


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """提供一个 FastAPI TestClient 用于端到端 API 测试。"""
    sandbox_store.clear()
    snapshot_store.clear()
    
    with TestClient(app) as client:
        print("\n--- TestClient Created (Session Scope) ---")
        yield client
    
    print("\n--- TestClient Teardown ---")
    sandbox_store.clear()
    snapshot_store.clear()


# ---------------------------------------------------------------------------
# Fixtures for Graph Collections (Test Data) - 重写以适应宏系统
# ---------------------------------------------------------------------------

# --- 基本流程 ---

@pytest.fixture
def linear_collection() -> GraphCollection:
    """一个简单的三节点线性图：A -> B -> C。
    节点B不再需要 template 运行时，直接在 prompt 字段中使用宏。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A", "data": {"runtime": "system.input", "value": "a story about a cat"}},
                # B现在直接在prompt字段中使用f-string宏
                {"id": "B", "data": {"runtime": "llm.default", "prompt": "{{ f'The story is: {nodes.A.output}' }}"}},
                # C依赖B的输出
                {"id": "C", "data": {"runtime": "llm.default", "prompt": "{{ nodes.B.llm_output }}"}}
            ]
        }
    })


@pytest.fixture
def parallel_collection() -> GraphCollection:
    """一个扇出再扇入的图 (A, B) -> C，使用 f-string 宏合并结果。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "source_A", "data": {"runtime": "system.input", "value": "Value A"}},
                {"id": "source_B", "data": {"runtime": "system.input", "value": "Value B"}},
                {
                    "id": "merger",
                    "data": {
                        # 这个节点甚至不需要运行时，宏在预处理阶段就完成了所有工作
                        "merged_value": "{{ f'Merged: {nodes.source_A.output} and {nodes.source_B.output}' }}"
                    }
                }
            ]
        }
    })


@pytest.fixture
def pipeline_collection() -> GraphCollection:
    """一个包含节点内运行时管道的图。
    现在宏系统是隐式的步骤0，所以我们测试一个显式的管道 `set_var | llm`。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "A",
                    "data": {
                        "runtime": ["system.set_world_var", "llm.default"],
                        # 这个宏会在预处理阶段被执行
                        "character_name": "{{ 'Sir Reginald' }}",
                        # set_world_var 的配置
                        "variable_name": "main_character",
                        "value": "{{ f'The brave knight, {self.character_name}' }}",
                        # llm.default 的配置
                        "prompt": "{{ f'Tell a story about {world.main_character}.' }}"
                    }
                }
            ]
        }
    })

# --- 状态管理与宏功能 ---

@pytest.fixture
def world_vars_collection() -> GraphCollection:
    """一个测试世界变量（world_state）设置和读取的图。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "setter", "data": {
                    "runtime": "system.set_world_var",
                    "variable_name": "theme",
                    "value": "cyberpunk"
                }},
                # reader 节点不再需要 template 运行时
                {"id": "reader", "data": {
                    "output": "{{ f'The theme is: {world.theme}' }}"
                }}
            ]
        }
    })

@pytest.fixture
def macro_collection() -> GraphCollection:
    """一个专门用于测试宏系统多种功能的图。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                # 节点A：使用宏进行计算和修改 world state
                {
                    "id": "A_modify_world",
                    "data": {
                        "script": "{{ world.update({'initial_hp': 100, 'is_ready': True}) }}",
                        "damage": "{{ 10 + random.randint(5, 15) }}"
                    }
                },
                # 节点B：依赖A，读取 world state 和 A 的结果
                {
                    "id": "B_read_and_decide",
                    "data": {
                        "prompt": """{{
'The player is ready. ' if world.is_ready else 'The player is not ready. ' +
f'Initial HP was {world.initial_hp}. ' +
f'Took {nodes.A_modify_world.damage} damage.'
                        }}"""
                    }
                }
            ]
        }
    })

@pytest.fixture
def execute_runtime_collection() -> GraphCollection:
    """一个测试 system.execute 运行时的图，用于二次求值。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                # 节点A: 产生一个包含可执行代码的字符串
                {
                    "id": "A_generate_code",
                    "data": {"output": "{{ 'world.player_status = \"empowered\"' }}"}
                },
                # 节点B: 使用 system.execute 运行来自 A 的代码
                {
                    "id": "B_execute_code",
                    "data": {
                        "runtime": "system.execute",
                        "code": "{{ nodes.A_generate_code.output }}"
                    }
                }
            ]
        }
    })

# --- 错误与边界情况 ---

@pytest.fixture
def cyclic_collection() -> GraphCollection:
    """一个包含环路的图，用于测试环路检测。此 fixture 无需修改。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A", "data": {"prompt": "{{ nodes.C.output }}"}},
                {"id": "B", "data": {"prompt": "{{ nodes.A.output }}"}},
                {"id": "C", "data": {"prompt": "{{ nodes.B.output }}"}}
            ]
        }
    })


@pytest.fixture
def failing_node_collection() -> GraphCollection:
    """一个包含注定会失败的节点的图。失败原因从Jinja2错误改为Python NameError。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A_ok", "data": {"runtime": "system.input", "value": "start"}},
                # 节点 B 会因为引用未定义的 Python 变量而失败
                {"id": "B_fail", "data": {"output": "{{ non_existent_variable }}"}},
                # 节点 C 依赖于失败的节点 B，应该被跳过
                {"id": "C_skip", "data": {"output": "{{ nodes.B_fail.output }}"}},
                # 节点 D 不依赖于失败的分支，应该成功执行
                {"id": "D_independent", "data": {"runtime": "system.input", "value": "independent"}}
            ]
        }
    })


@pytest.fixture
def invalid_graph_no_main() -> dict:
    """一个无效的图定义，缺少 'main' 入口点。此 fixture 无需修改。"""
    return {
      "not_main": {
        "nodes": [
          {"id": "a", "data": {"runtime": "test"}}
        ]
      }
    }


# --- 图演化 (保持不变，因为其逻辑与宏系统正交) ---

@pytest.fixture
def graph_evolution_collection() -> GraphCollection:
    """
    一个用于测试图演化的特殊图。
    它会生成一个新的 GraphCollection 定义并将其存储在 world_state 中。
    """
    new_graph_dict = {
      "main": {
        "nodes": [
          { "id": "new_node", "data": { "output": "This is the evolved graph!" } }
        ]
      }
    }
    new_graph_json_string = json.dumps(new_graph_dict)
    
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "graph_generator",
                    "data": {
                        "runtime": "system.set_world_var",
                        "variable_name": "__graph_collection__",
                        "value": new_graph_json_string
                    }
                }
            ]
        }
    })
```

### test_02_evaluation_unit.py
```
# tests/test_02_evaluation_unit.py
import pytest
from uuid import uuid4

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
        code = """
x = 10
y = 20
if world.hp > 50:
    x + y
else:
    x - y
"""
        mock_eval_context["world"]["hp"] = 80
        assert await evaluate_expression(code, mock_eval_context) == 30
        
        mock_eval_context["world"]["hp"] = 40
        assert await evaluate_expression(code, mock_eval_context) == -10

    async def test_pre_imported_modules(self, mock_eval_context):
        """测试是否可以无需导入就直接使用预置模块。"""
        # 测试 random
        assert await evaluate_expression("random.randint(1, 1)", mock_eval_context) == 1
        # 测试 math
        assert await evaluate_expression("math.floor(3.9)", mock_eval_context) == 3
        # 测试 json
        json_str = await evaluate_expression("json.dumps({'a': 1})", mock_eval_context)
        assert json_str == '{"a": 1}'

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
```

### test_01_foundations.py
```
# tests/test_01_foundations.py
import pytest
from pydantic import ValidationError
from uuid import uuid4

# ---------------------------------------------------------------------------
# 导入被测试的类
# ---------------------------------------------------------------------------
from backend.models import GraphCollection, GenericNode, GraphDefinition
from backend.core.state_models import StateSnapshot, Sandbox, SnapshotStore
from backend.core.dependency_parser import build_dependency_graph


# ---------------------------------------------------------------------------
# Section 1: Core Data Models (`models.py`)
# - 这部分测试不受影响，因为模型验证逻辑没有改变。
# ---------------------------------------------------------------------------

class TestCoreModels:
    """测试核心数据模型：GenericNode, GraphDefinition, GraphCollection"""

    def test_generic_node_validation_success(self):
        """测试 GenericNode 的有效数据格式。"""
        # 字符串 runtime
        node1 = GenericNode(id="n1", data={"runtime": "test.runtime"})
        assert node1.id == "n1"
        assert node1.data["runtime"] == "test.runtime"
        
        # 字符串列表 runtime
        node2 = GenericNode(id="n2", data={"runtime": ["step1", "step2"]})
        assert node2.data["runtime"] == ["step1", "step2"]
        
        # 宏系统下，节点甚至可以没有 runtime，作为纯数据持有者
        node3 = GenericNode(id="n3", data={"value": "{{ 1 + 1 }}"})
        assert "runtime" not in node3.data

    def test_generic_node_validation_fails(self):
        """测试 GenericNode 的无效数据格式（除了缺少runtime）。"""
        # runtime 类型错误（非字符串或字符串列表）
        with pytest.raises(ValidationError, match="'runtime' must be a string or a list of strings"):
            GenericNode(id="n2", data={"runtime": 123})
            
        with pytest.raises(ValidationError, match="'runtime' must be a string or a list of strings"):
            GenericNode(id="n3", data={"runtime": ["step1", 2]})

    def test_graph_collection_validation(self):
        """测试 GraphCollection 模型的验证逻辑。"""
        # 1. 有效数据
        valid_data = {"main": {"nodes": [{"id": "a", "data": {"runtime": "test"}}]}}
        collection = GraphCollection.model_validate(valid_data)
        assert "main" in collection.root
        assert isinstance(collection.root["main"], GraphDefinition)
        assert len(collection.root["main"].nodes) == 1

        # 2. 缺少 "main" 图应该失败
        with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
            GraphCollection.model_validate({"other_graph": {"nodes": []}})

        # 3. 节点验证失败会冒泡到顶层
        with pytest.raises(ValidationError, match="must be a string or a list of strings"):
            GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "data": {"runtime": 123}}]}})


# ---------------------------------------------------------------------------
# Section 2: Sandbox Models (`core/state_models.py`)
# - 这部分测试不受影响，因为状态管理模型没有改变。
# ---------------------------------------------------------------------------

class TestSandboxModels:
    """测试沙盒相关的数据模型：StateSnapshot, Sandbox, SnapshotStore"""

    @pytest.fixture
    def sample_graph_collection(self) -> GraphCollection:
        """提供一个简单的 GraphCollection 用于创建快照。"""
        return GraphCollection.model_validate({
            "main": {"nodes": [{"id": "a", "data": {"runtime": "test"}}]}
        })

    def test_state_snapshot_creation(self, sample_graph_collection: GraphCollection):
        """测试 StateSnapshot 的创建和默认值。"""
        sandbox_id = uuid4()
        snapshot = StateSnapshot(
            sandbox_id=sandbox_id,
            graph_collection=sample_graph_collection
        )
        assert snapshot.sandbox_id == sandbox_id
        assert snapshot.id is not None
        assert snapshot.created_at is not None
        assert snapshot.parent_snapshot_id is None
        assert snapshot.world_state == {}

    def test_state_snapshot_is_immutable(self, sample_graph_collection: GraphCollection):
        """关键测试：验证 StateSnapshot 是不可变的。"""
        snapshot = StateSnapshot(
            sandbox_id=uuid4(),
            graph_collection=sample_graph_collection
        )
        with pytest.raises(ValidationError, match="Instance is frozen"):
            snapshot.world_state = {"new_key": "new_value"}
        
        with pytest.raises(TypeError, match="unhashable type"):
             {snapshot}

    def test_snapshot_store(self, sample_graph_collection: GraphCollection):
        """测试 SnapshotStore 的基本功能。"""
        store = SnapshotStore()
        s1_id, s2_id = uuid4(), uuid4()
        box1_id, box2_id = uuid4(), uuid4()

        s1 = StateSnapshot(id=s1_id, sandbox_id=box1_id, graph_collection=sample_graph_collection)
        s2 = StateSnapshot(id=s2_id, sandbox_id=box1_id, graph_collection=sample_graph_collection)

        store.save(s1)
        store.save(s2)

        assert store.get(s1_id) == s1
        assert store.get(uuid4()) is None
        assert len(store.find_by_sandbox(box1_id)) == 2
        assert len(store.find_by_sandbox(box2_id)) == 0
        with pytest.raises(ValueError, match=f"Snapshot with id {s1_id} already exists"):
            store.save(s1)


# ---------------------------------------------------------------------------
# Section 3: Dependency Parser (`core/dependency_parser.py`)
# - 这部分测试不受影响，因为解析器在宏求值前运行，并且只关心 `{{ nodes.* }}` 语法。
# ---------------------------------------------------------------------------

class TestDependencyParser:
    """测试依赖解析器 build_dependency_graph 的各种情况。"""

    def test_simple_dependency(self):
        """测试：B 依赖 A"""
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            {"id": "B", "data": {"value": "Ref: {{ nodes.A.output }}"}}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()
        assert deps["B"] == {"A"}

    def test_multiple_dependencies(self):
        """测试：C 依赖 A 和 B"""
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            {"id": "B", "data": {"runtime": "input"}},
            {"id": "C", "data": {"value": "ValA: {{ nodes.A.val }}, ValB: {{ nodes.B.val }}"}}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["C"] == {"A", "B"}
        assert deps["A"] == set()
        assert deps["B"] == set()

    def test_dependency_in_nested_structure(self):
        """测试：依赖项在深层嵌套的字典和列表中"""
        nodes = [
            {"id": "source", "data": {"runtime": "input"}},
            {"id": "consumer", "data": {
                "config": {
                    "param1": "Value from {{ nodes.source.output }}",
                    "nested_list": [1, 2, {"key": "and {{ nodes.source.another_output }}"}]
                }
            }}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["consumer"] == {"source"}

    def test_no_dependencies(self):
        """测试：节点不依赖于任何其他节点"""
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            {"id": "B", "data": {"runtime": "input"}},
        ]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()
        assert deps["B"] == set()

    def test_ignores_non_node_macros(self):
        """关键测试：解析器应忽略 {{ world.* }}, {{ run.* }} 等非节点依赖的宏"""
        nodes = [
            {"id": "A", "data": {"value": "{{ world.x + run.y + session.z }}"}}
        ]
        deps = build_dependency_graph(nodes)
        assert deps["A"] == set()

    def test_dependency_on_nonexistent_node_is_ignored(self):
        """
        关键测试：依赖于图中不存在的节点（即子图的输入占位符）不应被视为依赖。
        """
        nodes = [
            {"id": "A", "data": {"runtime": "input"}},
            # 节点 B 引用了 'placeholder_input'，但这个 ID 不在当前节点列表中
            {"id": "B", "data": {"value": "Got: {{ nodes.placeholder_input.value }}"}}
        ]
        deps = build_dependency_graph(nodes)
        
        # 节点 B 的依赖集应该为空，因为它引用的节点不是当前图的一部分。
        assert deps["A"] == set()
        assert deps["B"] == set()
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

# ---------------------------------------------------------------------------
# Section 1: Sandbox Lifecycle E2E Tests
# ---------------------------------------------------------------------------

class TestApiSandboxLifecycle:
    """测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        """
        一个完整的端到端 happy path 测试。
        这个测试的逻辑基本不变，因为它不关心图内部的实现，只关心 API 交互。
        """
        # --- 1. 创建沙盒 ---
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Test Sandbox"},
            json={
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {"player": "Humphrey"} 
            }
        )
        assert response.status_code == 200
        sandbox_data = response.json()
        assert sandbox_data["name"] == "E2E Test Sandbox"
        sandbox_id = sandbox_data["id"]
        
        assert sandbox_data["head_snapshot_id"] is not None
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        # --- 2. 执行一个步骤 ---
        response = test_client.post(
            f"/api/sandboxes/{sandbox_id}/step",
            json={"user_message": "A test input"} # Body 现在是 user_input
        )
        assert response.status_code == 200
        step1_snapshot_data = response.json()
        
        assert step1_snapshot_data["id"] != genesis_snapshot_id
        assert step1_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id
        step1_snapshot_id = step1_snapshot_data["id"]
        
        # 验证执行结果是否符合预期（可选，但推荐）
        run_output = step1_snapshot_data.get("run_output", {})
        assert "C" in run_output
        assert "LLM_RESPONSE_FOR" in run_output["C"]["llm_output"]

        # --- 3. 获取历史记录 ---
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200
        history = response.json()
        
        assert len(history) == 2
        history_ids = {item["id"] for item in history}
        assert genesis_snapshot_id in history_ids
        assert step1_snapshot_id in history_ids

        # --- 4. 回滚到创世快照 ---
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200
        assert response.json() == {"message": f"Sandbox reverted to snapshot {genesis_snapshot_id}"}
        
        # --- 5. 验证回滚后的状态 ---
        response = test_client.post(
            f"/api/sandboxes/{sandbox_id}/step",
            json={"user_message": "A different input"}
        )
        assert response.status_code == 200
        step2_snapshot_data = response.json()
        
        # 验证新快照的父节点是回滚后的创世快照
        assert step2_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id


# ---------------------------------------------------------------------------
# Section 2: API Error Handling E2E Tests
# ---------------------------------------------------------------------------

class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        """
        关键修改：测试当图定义无效时（如缺少 main），API 返回 422 错误。
        """
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid Sandbox"},
            json={
                "graph_collection": invalid_graph_no_main,
                "initial_state": {}
            }
        )

        # FastAPI 对 Pydantic RootModel 的验证失败会返回 422
        assert response.status_code == 422 
        error_data = response.json()
        
        # 检查 FastAPI 标准的 validation error 响应体结构
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list) and len(error_data["detail"]) > 0

        first_error = error_data["detail"][0]
        assert first_error["type"] == "value_error"
        assert "A 'main' graph must be defined as the entry point." in first_error["msg"]
        
        # 验证错误位置指向了请求体中的正确字段
        assert first_error["loc"] == ["body", "graph_collection", "root"]

    def test_create_sandbox_with_invalid_pydantic_payload(self, test_client: TestClient):
        """测试一个在 Pydantic 层就无法解析的请求体。"""
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid Payload"},
            json={
                "graph_collection": "this-should-be-a-dict", # 错误类型
                "initial_state": "this-should-be-a-dict"
            }
        )

        assert response.status_code == 422
        error_data = response.json()["detail"]
        assert any("Input should be a valid dictionary" in e["msg"] for e in error_data)
        assert any(["body", "graph_collection"] == e["loc"] for e in error_data)

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        """测试对不存在的沙盒进行操作。"""
        nonexistent_id = uuid4()
        
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        assert response.json()["detail"] == "Sandbox not found."
        
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        # GET 历史通常返回空列表而不是 404，这是一种常见实践
        assert response.status_code == 200
        assert response.json() == []

        response = test_client.put(
            f"/api/sandboxes/{nonexistent_id}/revert",
            params={"snapshot_id": uuid4()}
        )
        assert response.status_code == 404
        assert "Sandbox or Snapshot not found" in response.json()["detail"]
    
    def test_revert_to_nonexistent_snapshot(self, test_client: TestClient, linear_collection: GraphCollection):
        """测试回滚到一个不存在的快照。"""
        # 先创建一个有效的沙盒
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Revert Test"},
            json={"graph_collection": linear_collection.model_dump()}
        )
        assert response.status_code == 200
        sandbox_id = response.json()["id"]
        
        nonexistent_id = uuid4()
        
        # 尝试回滚
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": nonexistent_id}
        )
        assert response.status_code == 404
        assert "Sandbox or Snapshot not found" in response.json()["detail"]
```

### test_03_engine_integration.py
```
# tests/test_03_engine_integration.py
import pytest
from uuid import uuid4

# ---------------------------------------------------------------------------
# 导入被测试的类和所需的 Fixtures
# ---------------------------------------------------------------------------
from backend.core.engine import ExecutionEngine
from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

# 注意：这个文件中的测试函数会自动接收来自 conftest.py 的 fixtures，
# 例如 test_engine, linear_collection, parallel_collection 等。

# ---------------------------------------------------------------------------
# Section 1: Core Execution Flow Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineCoreFlows:
    """测试引擎的核心执行流程，如线性、并行和管道，使用新的宏系统。"""

    async def test_engine_linear_flow(self, test_engine: ExecutionEngine, linear_collection: GraphCollection):
        """测试简单的线性工作流 A -> B -> C，验证数据在宏之间正确传递。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=linear_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        assert "A" in run_output
        assert run_output["A"]["output"] == "a story about a cat"
        
        assert "B" in run_output
        expected_prompt_b = "The story is: a story about a cat"
        # 验证宏已执行，prompt 字段是最终结果
        assert run_output["B"]["prompt"] == expected_prompt_b
        assert run_output["B"]["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt_b}]"
        
        assert "C" in run_output
        expected_prompt_c = run_output["B"]["llm_output"]
        assert run_output["C"]["prompt"] == expected_prompt_c
        assert run_output["C"]["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt_c}]"

    async def test_engine_parallel_flow(self, test_engine: ExecutionEngine, parallel_collection: GraphCollection):
        """测试并行分支的图，验证扇出和扇入。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=parallel_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output
        assert len(run_output) == 3
        # 验证 merger 节点，它的 merged_value 字段应该已经被宏计算好
        assert run_output["merger"]["merged_value"] == "Merged: Value A and Value B"

    async def test_engine_runtime_pipeline(self, test_engine: ExecutionEngine, pipeline_collection: GraphCollection):
        """测试单个节点内的运行时管道，并验证宏预处理与运行时的交互。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=pipeline_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 验证 world_state 被 set_world_var 运行时修改
        assert final_snapshot.world_state["main_character"] == "The brave knight, Sir Reginald"

        # 验证 llm.default 运行时使用了被修改后的 world_state
        run_output = final_snapshot.run_output
        node_a_result = run_output["A"]
        
        expected_prompt = "Tell a story about The brave knight, Sir Reginald."
        assert node_a_result["prompt"] == expected_prompt
        assert node_a_result["llm_output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"


# ---------------------------------------------------------------------------
# Section 2: State and Macro Advanced Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineStateAndMacros:
    """测试引擎如何处理持久化状态，以及更高级的宏功能。"""

    async def test_world_state_persists_and_macros_read_it(self, test_engine: ExecutionEngine, world_vars_collection: GraphCollection):
        """验证 world_state 能被设置，并能被后续节点的宏读取。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=world_vars_collection)
        
        snapshot_after_set = await test_engine.step(initial_snapshot, {})
        
        assert snapshot_after_set.world_state == {"theme": "cyberpunk"}
        # 验证 reader 节点通过宏成功读取了 world_state
        assert snapshot_after_set.run_output["reader"]["output"] == "The theme is: cyberpunk"

    async def test_graph_evolution(self, test_engine: ExecutionEngine, graph_evolution_collection: GraphCollection):
        """高级测试：验证图可以修改自己的逻辑并影响后续执行。此测试逻辑不变。"""
        genesis_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=graph_evolution_collection)
        
        snapshot_after_evolution = await test_engine.step(genesis_snapshot, {})
        
        assert "__graph_collection__" in snapshot_after_evolution.world_state
        
        new_graph_def = snapshot_after_evolution.graph_collection
        assert len(new_graph_def.root["main"].nodes) == 1
        assert new_graph_def.root["main"].nodes[0].id == "new_node"
        
        final_snapshot = await test_engine.step(snapshot_after_evolution, {})

        run_output = final_snapshot.run_output
        assert "new_node" in run_output
        assert run_output["new_node"]["output"] == "This is the evolved graph!"

    async def test_execute_runtime_integration(self, test_engine: ExecutionEngine, execute_runtime_collection: GraphCollection):
        """集成测试：验证 system.execute 能在引擎流程中正确执行二次求值。"""
        initial_snapshot = StateSnapshot(
            sandbox_id=uuid4(), 
            graph_collection=execute_runtime_collection,
            world_state={"player_status": "normal"}
        )

        final_snapshot = await test_engine.step(initial_snapshot, {})

        # 验证 B_execute_code 的输出
        run_output = final_snapshot.run_output
        # 副作用宏返回 None
        assert run_output["B_execute_code"]["output"] is None

        # 最关键的验证：world_state 是否被二次求值的代码所修改
        assert final_snapshot.world_state["player_status"] == "empowered"

# ---------------------------------------------------------------------------
# Section 3: Error and Edge Case Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEngineErrorHandling:
    """测试引擎在错误和边界情况下的鲁棒性。"""

    async def test_engine_detects_cycle(self, test_engine: ExecutionEngine, cyclic_collection: GraphCollection):
        """测试引擎在图运行初始化时能正确检测到环路。此测试逻辑不变。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=cyclic_collection)
        
        with pytest.raises(ValueError, match="Cycle detected"):
            await test_engine.step(initial_snapshot, {})

    async def test_engine_handles_failure_and_skips_downstream(self, test_engine: ExecutionEngine, failing_node_collection: GraphCollection):
        """测试当一个节点因宏执行失败时，下游节点被正确跳过。"""
        initial_snapshot = StateSnapshot(sandbox_id=uuid4(), graph_collection=failing_node_collection)
        
        final_snapshot = await test_engine.step(initial_snapshot, {})
        
        run_output = final_snapshot.run_output

        # 验证成功和独立的节点
        assert "error" not in run_output.get("A_ok", {})
        assert "error" not in run_output.get("D_independent", {})
        assert run_output["D_independent"]["output"] == "independent"

        # 验证失败的节点
        assert "error" in run_output.get("B_fail", {})
        # 错误原因现在是宏预处理失败
        assert run_output["B_fail"]["failed_step"] == "pre-processing"
        # 错误信息现在是 Python 的 NameError
        assert "Macro evaluation failed" in run_output["B_fail"]["error"]
        assert "name 'non_existent_variable' is not defined" in run_output["B_fail"]["error"]
        
        # 验证被跳过的下游节点
        assert "status" in run_output.get("C_skip", {})
        assert run_output["C_skip"]["status"] == "skipped"
        assert run_output["C_skip"]["reason"] == "Upstream failure of node B_fail."
```
