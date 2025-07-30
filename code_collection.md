### conftest.py
```
# tests/conftest.py
import pytest
from backend.models import GraphCollection
# 导入所需的类
from backend.core.registry import RuntimeRegistry
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime, SetGlobalVariableRuntime

# --- Fixtures for Graph Collections ---

@pytest.fixture
def linear_collection() -> GraphCollection:
    """一个简单的三节点线性图：A -> B -> C，通过宏隐式依赖。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "node_A", "data": {"runtime": "system.input", "value": "A story about a cat."}},
                {"id": "node_B", "data": {"runtime": "system.template", "template": "The story is: {{ nodes.node_A.output }}"}},
                {"id": "node_C", "data": {"runtime": "system.template", "template": "Final words: {{ nodes.node_B.output }}"}}
            ]
        }
    })

@pytest.fixture
def parallel_collection() -> GraphCollection:
    """一个扇出再扇入的图，测试并行执行。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "source_A", "data": {"runtime": "system.input", "value": "Value A"}},
                {"id": "source_B", "data": {"runtime": "system.input", "value": "Value B"}},
                {"id": "processor_A", "data": {"runtime": "llm.default", "prompt": "Process {{ nodes.source_A.output }}"}},
                {"id": "processor_B", "data": {"runtime": "llm.default", "prompt": "Process {{ nodes.source_B.output }}"}},
                {"id": "merger", "data": {
                    "runtime": "system.template",
                    "template": "Merged: {{ nodes.processor_A.summary }} and {{ nodes.processor_B.summary }}"
                }}
            ]
        }
    })

@pytest.fixture
def cyclic_collection() -> GraphCollection:
    """一个包含环路的图，用于测试环路检测。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A", "data": {"runtime": "system.template", "template": "{{ nodes.C.output }}"}},
                {"id": "B", "data": {"runtime": "system.template", "template": "{{ nodes.A.output }}"}},
                {"id": "C", "data": {"runtime": "system.template", "template": "{{ nodes.B.output }}"}}
            ]
        }
    })

@pytest.fixture
def pipeline_collection() -> GraphCollection:
    """一个包含节点内运行时管道的图。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A", "data": {"runtime": "system.input", "value": "a cheerful dog"}},
                {
                    "id": "B",
                    "data": {
                        "runtime": ["system.template", "llm.default"],
                        "template": "Create a story about {{ nodes.A.output }}.",
                    }
                }
            ]
        }
    })

@pytest.fixture
def global_vars_collection() -> GraphCollection:
    """一个测试全局变量设置和读取的图。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "setter", "data": {
                    "runtime": "system.set_global_var",
                    "variable_name": "theme",
                    "value": "cyberpunk"
                }},
                {"id": "reader", "data": {
                    "runtime": "system.template",
                    "template": "The theme is: {{ vars.theme }}"
                }}
            ]
        }
    })

@pytest.fixture(scope="module") # 'module' scope: 这个fixture在整个测试模块中只执行一次
def populated_registry() -> RuntimeRegistry:
    """提供一个预先填充了所有基础运行时的注册表实例。"""
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("system.template", TemplateRuntime)
    registry.register("llm.default", LLMRuntime)
    registry.register("system.set_global_var", SetGlobalVariableRuntime)
    return registry
```

### test_03_templating_and_runtimes.py
```
# tests/test_03_templating_and_runtimes.py
import pytest
from backend.core.templating import render_template
from backend.core.types import ExecutionContext
from backend.models import GraphCollection, GraphDefinition
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime, SetGlobalVariableRuntime

# --- Templating Tests ---

@pytest.fixture
def mock_context() -> ExecutionContext:
    """提供一个可复用的、空的 ExecutionContext。"""
    return ExecutionContext(
        state={},
        current_graph_def=GraphDefinition(nodes=[]),
        graph_collection=GraphCollection.model_validate({"main": {"nodes": []}})
    )

@pytest.mark.asyncio
async def test_render_simple_variable_access(mock_context: ExecutionContext):
    """测试基本的节点输出访问 {{ nodes.NODE_ID.OUTPUT_KEY }}"""
    mock_context.state = {"node_A": {"output": "Success"}}
    template_str = "The result from node A is: {{ nodes.node_A.output }}"
    result = await render_template(template_str, mock_context)
    assert result == "The result from node A is: Success"

@pytest.mark.asyncio
async def test_render_session_and_global_vars_access(mock_context: ExecutionContext):
    """测试访问会话信息和全局变量"""
    mock_context.session_info = {"conversation_turn": 3}
    mock_context.global_vars = {"user_name": "Alice"}
    template_str = "User: {{ vars.user_name }}, Turn: {{ session.conversation_turn }}"
    result = await render_template(template_str, mock_context)
    assert result == "User: Alice, Turn: 3"
    
@pytest.mark.asyncio
async def test_render_raises_error_on_missing_variable(mock_context: ExecutionContext):
    """测试当变量不存在时，render_template会因为StrictUndefined而抛出IOError。"""
    template_str = "Value is {{ nodes.non_existent.output }}"

    with pytest.raises(IOError, match="Template rendering failed: 'dict object' has no attribute 'non_existent'"):
        await render_template(template_str, mock_context)

# --- Runtimes Unit Tests ---

@pytest.mark.asyncio
async def test_input_runtime():
    runtime = InputRuntime()
    result = await runtime.execute(step_input={"value": "Hello"})
    assert result == {"output": "Hello"}

@pytest.mark.asyncio
async def test_template_runtime(mock_context: ExecutionContext):
    runtime = TemplateRuntime()
    mock_context.state = {"upstream": {"data": "World"}}
    
    result = await runtime.execute(
        step_input={"template": "Hello {{ nodes.upstream.data }}"},
        context=mock_context
    )
    assert result == {"output": "Hello World"}

@pytest.mark.asyncio
async def test_llm_runtime(mock_context: ExecutionContext, mocker):
    mocker.patch("asyncio.sleep", return_value=None)
    runtime = LLMRuntime()
    
    result = await runtime.execute(
        step_input={"prompt": "Test prompt"},
        context=mock_context
    )
    
    assert "llm_output" in result
    assert result["llm_output"] == "LLM_RESPONSE_FOR:[Test prompt]"
    assert "summary" in result

@pytest.mark.asyncio
async def test_set_global_variable_runtime(mock_context: ExecutionContext):
    runtime = SetGlobalVariableRuntime()
    
    await runtime.execute(
        step_input={"variable_name": "my_var", "value": 123},
        context=mock_context
    )
    
    assert "my_var" in mock_context.global_vars
    assert mock_context.global_vars["my_var"] == 123
```

### __init__.py
```

```

### test_02_engine.py
```
# tests/test_02_engine.py
import pytest
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import RuntimeRegistry # 导入类型，而不是实例

# 注意：我们不再从全局导入 runtime_registry 实例

@pytest.mark.asyncio
async def test_engine_linear_flow(linear_collection: GraphCollection, populated_registry: RuntimeRegistry):
    """测试简单的线性工作流，验证隐式依赖和数据传递。"""
    # 使用注入的、已填充的注册表
    engine = ExecutionEngine(registry=populated_registry)
    final_state = await engine.execute(linear_collection)
    
    assert "node_A" in final_state
    # 验证 node.data 和 InputRuntime 的输出合并了
    assert final_state["node_A"]["value"] == "A story about a cat."
    assert final_state["node_A"]["output"] == "A story about a cat."
    
    assert "node_B" in final_state
    assert final_state["node_B"]["output"] == "The story is: A story about a cat."
    
    assert "node_C" in final_state
    assert final_state["node_C"]["output"] == "Final words: The story is: A story about a cat."

@pytest.mark.asyncio
async def test_engine_parallel_flow(parallel_collection: GraphCollection, populated_registry: RuntimeRegistry, mocker):
    """测试并行分支的图，验证并发执行。"""
    mocker.patch("asyncio.sleep", return_value=None)
    engine = ExecutionEngine(registry=populated_registry)
    final_state = await engine.execute(parallel_collection)
    
    assert len(final_state) == 5
    expected_merged = "Merged: Summary of 'Process Value A...' and Summary of 'Process Value B...'"
    assert final_state["merger"]["output"] == expected_merged

@pytest.mark.asyncio
async def test_engine_detects_cycle(cyclic_collection: GraphCollection, populated_registry: RuntimeRegistry):
    """测试引擎在初始化时能正确检测到环路。"""
    engine = ExecutionEngine(registry=populated_registry)
    with pytest.raises(ValueError, match="Cycle detected"):
        await engine.execute(cyclic_collection)

@pytest.mark.asyncio
async def test_engine_runtime_pipeline(pipeline_collection: GraphCollection, populated_registry: RuntimeRegistry, mocker):
    """测试单个节点内的运行时管道，并验证'pipeline_state'的合并行为。"""
    mocker.patch("asyncio.sleep", return_value=None)
    engine = ExecutionEngine(registry=populated_registry)
    final_state = await engine.execute(pipeline_collection)

    assert "B" in final_state
    node_b_result = final_state["B"]
    
    expected_prompt = "Create a story about a cheerful dog."
    expected_llm_output = f"LLM_RESPONSE_FOR:[{expected_prompt}]"

    # 验证 pipeline_state 的合并行为
    assert node_b_result["template"] == "Create a story about {{ nodes.A.output }}."
    assert node_b_result["output"] == expected_prompt  # TemplateRuntime's output key
    assert node_b_result["llm_output"] == expected_llm_output

@pytest.mark.asyncio
async def test_engine_handles_failure_and_skips_downstream(populated_registry: RuntimeRegistry):
    """测试当一个节点失败时，下游节点被正确跳过。"""
    collection = GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A", "data": {"runtime": "system.input", "value": "start"}},
                {"id": "B", "data": {"runtime": "system.template", "template": "{{ undefined.var }}"}},
                {"id": "C", "data": {"runtime": "system.template", "template": "Value: {{ nodes.B.output }}"}},
                {"id": "D", "data": {"runtime": "system.input", "value": "independent"}}
            ]
        }
    })
    
    engine = ExecutionEngine(registry=populated_registry)
    final_state = await engine.execute(collection)
    
    assert "error" not in final_state.get("A", {})
    assert "error" not in final_state.get("D", {})

    assert "error" in final_state.get("B", {})
    # 修复：错误信息中现在包含了 Jinja2 的具体错误
    assert "Failed at step 1" in final_state["B"]["error"]
    assert "'undefined' is undefined" in final_state["B"]["error"] # 更精确的断言
    
    assert "status" in final_state.get("C", {})
    assert final_state["C"]["status"] == "skipped"
    assert final_state["C"]["reason"] == "Upstream failure of node B."

@pytest.mark.asyncio
async def test_engine_global_vars(global_vars_collection: GraphCollection, populated_registry: RuntimeRegistry):
    """测试全局变量的设置和读取。"""
    engine = ExecutionEngine(registry=populated_registry)
    final_state = await engine.execute(global_vars_collection)
    
    assert "setter" in final_state
    assert "reader" in final_state
    assert final_state["reader"]["output"] == "The theme is: cyberpunk"
```

### test_01_models_and_parsers.py
```
# tests/test_01_models_and_parsers.py
import pytest
from pydantic import ValidationError

from backend.models import GraphCollection, GenericNode
from backend.core.dependency_parser import build_dependency_graph

# --- Model Tests ---
def test_generic_node_validation():
    # 你的节点验证测试保持不变，它依然有效
    valid_data = {"id": "1", "data": {"runtime": "test"}}
    node = GenericNode(**valid_data)
    assert node.id == "1"
    assert node.data["runtime"] == "test"

    with pytest.raises(ValidationError, match="must contain a 'runtime' field"):
        GenericNode(id="2", data={})

def test_graph_collection_validation():
    """测试 GraphCollection 模型的验证逻辑。"""
    # 1. 有效数据
    valid_data = {"main": {"nodes": [{"id": "a", "data": {"runtime": "test"}}]}}
    collection = GraphCollection.model_validate(valid_data)
    assert "main" in collection.graphs
    assert len(collection.graphs["main"].nodes) == 1

    # 2. 缺少 "main" 图应该失败
    with pytest.raises(ValidationError, match="A 'main' graph must be defined"):
        GraphCollection.model_validate({"other_graph": {"nodes": []}})

    # 3. 节点验证（继承自 GenericNode）
    with pytest.raises(ValidationError, match="must contain a 'runtime' field"):
        GraphCollection.model_validate({"main": {"nodes": [{"id": "a", "data": {}}]}})

# --- Dependency Parser Tests ---
def test_dependency_parser_simple():
    """测试依赖解析器处理简单情况。"""
    nodes = [
        {"id": "A", "data": {"runtime": "input"}},
        {"id": "B", "data": {"runtime": "template", "template": "Ref: {{ nodes.A.output }}"}}
    ]
    deps = build_dependency_graph(nodes)
    assert deps["A"] == set()
    assert deps["B"] == {"A"}

def test_dependency_parser_multiple_deps():
    """测试一个节点依赖多个上游节点。"""
    nodes = [
        {"id": "A", "data": {"runtime": "input"}},
        {"id": "B", "data": {"runtime": "input"}},
        {"id": "C", "data": {"runtime": "template", "template": "ValA: {{ nodes.A.val }}, ValB: {{ nodes.B.val }}"}}
    ]
    deps = build_dependency_graph(nodes)
    assert deps["C"] == {"A", "B"}

def test_dependency_parser_recursive():
    """测试解析器能处理嵌套的数据结构。"""
    nodes = [
        {"id": "A", "data": {"runtime": "input"}},
        {"id": "B", "data": {
            "runtime": "complex",
            "config": {
                "param1": "Value from {{ nodes.A.output }}",
                "nested_list": [1, 2, "and {{ nodes.A.another_output }}"]
            }
        }}
    ]
    deps = build_dependency_graph(nodes)
    assert deps["B"] == {"A"}

def test_dependency_parser_ignores_non_node_macros():
    """测试解析器应忽略 {{ vars... }} 和 {{ session... }} 等宏。"""
    nodes = [
        {"id": "A", "data": {"runtime": "template", "template": "{{ vars.x }} and {{ session.y }}"}}
    ]
    deps = build_dependency_graph(nodes)
    assert deps["A"] == set()
```
