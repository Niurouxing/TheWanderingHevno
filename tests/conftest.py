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


@pytest.fixture
def concurrent_write_collection() -> GraphCollection:
    """
    一个专门用于测试并发写入的图。
    - incrementer_A 和 incrementer_B 没有相互依赖，引擎会并行执行它们。
    - 两个节点都对同一个 world.counter 变量执行多次非原子操作 (read-modify-write)。
    - 如果没有锁，最终结果将几乎肯定小于 200。
    - 如果有宏级原子锁，每个宏的执行都是一个整体，结果必须是 200。
    """
    increment_loop_count = 100
    increment_code = f"""
for i in range({increment_loop_count}):
    # 这是一个典型的 read-modify-write 操作，非常容易产生竞态条件
    world.counter += 1
"""
    
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {
                "id": "incrementer_A",
                "run": [{"runtime": "system.execute", "config": {"code": increment_code}}]
            },
            {
                "id": "incrementer_B",
                "run": [{"runtime": "system.execute", "config": {"code": increment_code}}]
            },
            {
                "id": "reader",
                # depends_on 确保 reader 在两个写入者都完成后才执行
                "depends_on": ["incrementer_A", "incrementer_B"],
                "run": [{"runtime": "system.input", "config": {"value": "{{ world.counter }}"}}]
            }
        ]}
    })