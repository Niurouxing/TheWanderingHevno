# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from typing import Generator

# 1. 应用工厂导入
from backend.app import create_app

# 2. 共享的数据模型和契约导入
from backend.core.contracts import GraphCollection, Sandbox, StateSnapshot, Container

# --- Session-wide Fixtures ---

@pytest.fixture(scope="session")
def app() -> Generator[TestClient, None, None]:
    """
    一个会话级别的 fixture，用于创建一个完整的 FastAPI 应用实例。
    这个实例会完整地执行 lifespan，加载所有插件。
    """
    return create_app()

@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    """
    一个函数级别的 fixture，为每个测试提供一个干净的 TestClient 和状态。
    它依赖于会话级别的 app fixture。
    """
    container: Container = app.state.container
    
    # 获取由插件注册的存储服务
    sandbox_store: dict = container.resolve("sandbox_store")
    snapshot_store: any = container.resolve("snapshot_store")
    
    # 在每次测试前清理状态
    sandbox_store.clear()
    if hasattr(snapshot_store, 'clear'):
        snapshot_store.clear()

    with TestClient(app) as client:
        yield client
    
    # 测试后再次清理
    sandbox_store.clear()
    if hasattr(snapshot_store, 'clear'):
        snapshot_store.clear()


# --- Shared Graph Collection Fixtures ---
# 这些图定义被多个插件的测试所使用，放在这里以便共享。
# (这里的内容与您提供的 conftest.py 中的图定义 fixture 完全相同，因此省略以保持简洁)
# ... (linear_collection, parallel_collection, etc. fixtures go here) ...
# 注意：你需要将旧 conftest.py 中的所有 GraphCollection fixture 复制到这里。

@pytest.fixture
def linear_collection() -> GraphCollection:
    return GraphCollection.model_validate({
        "main": { "nodes": [
            {"id": "A", "run": [{"runtime": "system.input", "config": {"value": "a story about a cat"}}]},
            {"id": "B", "run": [{"runtime": "llm.default", "config": {"model": "mock/model", "prompt": "{{ f'The story is: {nodes.A.output}' }}"}}]},
            {"id": "C", "run": [{"runtime": "llm.default", "config": {"model": "mock/model", "prompt": "{{ nodes.B.llm_output }}"}}]}
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
    return GraphCollection.model_validate({
        "main": { "nodes": [{
            "id": "A",
            "run": [
                {"runtime": "system.set_world_var", "config": {"variable_name": "main_character", "value": "Sir Reginald"}},
                {"runtime": "system.input", "config": {"value": "A secret message"}},
                {"runtime": "llm.default", "config": {"model": "mock/model", "prompt": "{{ f'Tell a story about {world.main_character}. He just received this message: {pipe.output}' }}"}}
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

@pytest.fixture
def map_collection_basic() -> GraphCollection:
    base = {
        "main": { "nodes": [
            {"id": "character_provider", "run": [{"runtime": "system.input", "config": {"value": ["Aragorn", "Gandalf", "Legolas"]}}]},
            {"id": "global_setting_provider", "run": [{"runtime": "system.input", "config": {"value": "The Fellowship of the Ring"}}]},
            {"id": "character_processor_map", "run": [{"runtime": "system.map", "config": {
                "list": "{{ nodes.character_provider.output }}",
                "graph": "process_character",
                "using": {
                    "character_input": "{{ source.item }}",
                    "global_story_setting": "{{ nodes.global_setting_provider.output }}",
                    "character_index": "{{ source.index }}"
                }}}]}
            ]},
        "process_character": {"nodes": [{"id": "generate_bio", "run": [{"runtime": "llm.default", "config": {
            # 【修正】添加 model 字段
            "model": "mock/model",
            "prompt": "{{ f'Create a bio for {nodes.character_input.output} in the context of {nodes.global_story_setting.output}. Index: {nodes.character_index.output}' }}"
            }}]}]}
    }
    return GraphCollection.model_validate(base)


@pytest.fixture
def map_collection_with_collect(map_collection_basic: GraphCollection) -> GraphCollection:
    """
    一个测试 system.map 的 `collect` 功能的集合。
    - 它只从每个子图执行中提取 `generate_bio` 节点的 `llm_output` 字段。
    """
    # 【修正】通过参数接收 fixture，而不是直接调用
    base_data = map_collection_basic.model_dump()
    
    map_instruction = base_data["main"]["nodes"][2]["run"][0]
    # 添加 collect 字段
    map_instruction["config"]["collect"] = "{{ nodes.generate_bio.llm_output }}"
    
    return GraphCollection.model_validate(base_data)


@pytest.fixture
def map_collection_concurrent_write() -> GraphCollection:
    """
    一个测试在 map 内部并发修改 world_state 的集合。
    - 每个子图实例都会给 world.gold 增加10。
    - 如果没有原子锁，最终结果会因为竞态条件而不确定。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "task_provider",
                    "run": [{"runtime": "system.input", "config": {"value": list(range(10))}}] # 10个并行任务
                },
                {
                    "id": "concurrent_adder_map",
                    "run": [{
                        "runtime": "system.map",
                        "config": {
                            "list": "{{ nodes.task_provider.output }}",
                            "graph": "add_gold"
                            # using 是空的，因为子图不依赖 source
                        }
                    }]
                },
                {
                    "id": "reader",
                    "depends_on": ["concurrent_adder_map"],
                    "run": [{"runtime": "system.input", "config": {"value": "{{ world.gold }}"}}]
                }
            ]
        },
        "add_gold": {
            "nodes": [
                {
                    "id": "add_10_gold",
                    "run": [{"runtime": "system.execute", "config": {"code": "world.gold += 10"}}]
                }
            ]
        }
    })

@pytest.fixture
def map_collection_with_failure() -> GraphCollection:
    """
    一个 map 迭代中部分子图会失败的集合。
    - list 中有一个 str，会导致子图中的宏求值失败。
    - system.map 应该能正确返回所有结果，包括成功和失败的项。
    """
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "data_provider",
                    "run": [{"runtime": "system.input", "config": {"value": [{"name": "Alice"}, "Bob", {"name": "Charlie"}]}}]
                },
                {
                    "id": "mapper",
                    "run": [{
                        "runtime": "system.map",
                        "config": {
                            "list": "{{ nodes.data_provider.output }}",
                            "graph": "process_name",
                            # 【关键修正】将 source.item 映射到子图的占位符
                            "using": {
                                "character_data": "{{ source.item }}"
                            }
                        }
                    }]
                }
            ]
        },
        "process_name": {
            "nodes": [
                {
                    "id": "get_name",
                    "run": [{
                        "runtime": "system.input",
                        # 【关键修正】从占位符节点获取数据
                        # 当 character_data 是 "Bob" (str) 时，.name 会触发 AttributeError
                        "config": {"value": "{{ nodes.character_data.output.name }}"}
                    }]
                }
            ]
        }
    })



# ---------------------------------------------------------------------------
#  Codex System Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def codex_basic_data() -> dict:
    """
    分离的 Graph 和 Codex 数据，用于测试 `always_on` 和优先级。
    """
    graph_definition = {
        "main": {
            "nodes": [{
                "id": "invoke_test",
                "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "basic_info"}]}}]
            }]
        }
    }
    codices_data = {
        "basic_info": {
            "description": "基本的问候和介绍",
            "entries": [
                {"id": "greeting", "content": "你好，冒险者！", "priority": 10},
                {"id": "intro", "content": "欢迎来到这个奇幻的世界。", "priority": 5}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_keyword_and_priority_data() -> dict:
    """
    测试 `on_keyword` 触发模式和 `priority` 排序。
    """
    graph_definition = {
        "main": {
            "nodes": [
                {
                    "id": "invoke_weather",
                    "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "weather_lore", "source": "今天的魔法天气怎么样？"}]}}]
                },
                {
                    "id": "invoke_mood",
                    "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "mood_expressions", "source": "我很开心，因为天气很好。"}]}}]
                }
            ]
        }
    }
    codices_data = {
        "weather_lore": {
            "entries": [
                {"id": "sunny", "content": "阳光明媚，万里无云。", "trigger_mode": "on_keyword", "keywords": ["阳光", "晴朗"], "priority": 10},
                {"id": "rainy", "content": "外面下着大雨，带把伞吧。", "trigger_mode": "on_keyword", "keywords": ["下雨", "雨天"], "priority": 20},
                {"id": "magic_weather", "content": "魔法能量今天异常活跃，可能会有异象发生。", "trigger_mode": "on_keyword", "keywords": ["魔法天气", "异象"], "priority": 30}
            ]
        },
        "mood_expressions": {
            "entries": [
                {"id": "happy_mood", "content": "你看起来很高兴。", "trigger_mode": "on_keyword", "keywords": ["开心", "高兴", "快乐"], "priority": 5},
                {"id": "sad_mood", "content": "你似乎有些低落。", "trigger_mode": "on_keyword", "keywords": ["伤心", "低落"], "priority": 10}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_macro_eval_data() -> dict:
    """
    测试 Codex 条目内部宏求值的集合。
    使用三引号来避免引号冲突。
    """
    # 【修正】确保 graph_definition 是一个正确的字典
    graph_definition = {
        "main": {
            "nodes": [
                {
                    "id": "get_weather_report",
                    "run": [{
                        "runtime": "system.invoke",
                        "config": {
                            "from": [{"codex": "dynamic_entries", "source": "请告诉我关于秘密和夜幕下的世界。"}],
                            "debug": True
                        }
                    }]
                }
            ]
        }
    }
    codices_data = {
        "dynamic_entries": {
            "entries": [
                # 【修正】使用三引号 f-string，更清晰
                {"id": "night_info", "content": """{{ f"现在是{'夜晚' if world.is_night else '白天'}。" }}""", "is_enabled": "{{ world.is_night }}"},
                {"id": "level_message", "content": """{{ f'你的等级是：{world.player_level}级。' }}""", "priority": "{{ 100 if world.player_level > 3 else 0 }}"},
                {"id": "secret_keyword_entry", "content": """{{ f"你提到了'{trigger.matched_keywords[0]}'，这是一个秘密信息。" }}""", "trigger_mode": "on_keyword", "keywords": "{{ [world.hidden_keyword] }}", "priority": 50},
                {"id": "always_on_with_trigger_info", "content": """{{ f"原始输入是：'{trigger.source_text}'。" }}""", "trigger_mode": "always_on", "priority": 1}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_recursion_data() -> dict:
    """
    测试 Codex 的递归功能。
    """
    graph_definition = {
        "main": {"nodes": [{
            "id": "recursive_invoke",
            "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "recursive_lore", "source": "告诉我关于A"}], "recursion_enabled": True, "debug": True}}]
        }]}
    }
    codices_data = {
        "recursive_lore": {
            "config": {"recursion_depth": 5}, # 增加深度以确保测试通过
            "entries": [
                {"id": "entry_A", "content": "这是关于A的信息，它引出B。", "trigger_mode": "on_keyword", "keywords": ["A"], "priority": 10},
                {"id": "entry_B", "content": "B被A触发了，它又引出C。", "trigger_mode": "on_keyword", "keywords": ["B"], "priority": 20},
                {"id": "entry_C", "content": "C被B触发了，这是最终信息。", "trigger_mode": "on_keyword", "keywords": ["C"], "priority": 30},
                {"id": "entry_D_always_on", "content": "这是一个总是存在的背景信息。", "trigger_mode": "always_on", "priority": 5}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_invalid_structure_data() -> dict:
    """
    测试无效 Codex 结构时的错误处理。
    """
    graph_definition = {"main": {"nodes": [{"id": "invoke_invalid", "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "bad_codex"}]}}]}]}}
    codices_data = {
        "bad_codex": {
            "entries": [
                {"id": "valid_one", "content": "valid"},
                {"id": "invalid_one", "content": 123} # content 必须是字符串
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}


@pytest.fixture
def codex_concurrent_world_write_data() -> dict:
    """
    测试 `system.invoke` 内部宏对 `world_state` 的并发写入。
    """
    graph_definition = {
        "main": {
            "nodes": [
                {
                    "id": "invoke_and_increment",
                    "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "concurrent_codex", "source": "触发计数"}]}}]
                },
                {
                    "id": "read_counter",
                    "depends_on": ["invoke_and_increment"],
                    "run": [{"runtime": "system.input", "config": {"value": "{{ world.counter }}"}}]
                }
            ]
        }
    }
    codices_data = {
        "concurrent_codex": {
            "entries": [
                {"id": "increment_1", "content": "{{ world.counter = world.counter + 1; 'Incremented 1.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 10},
                {"id": "increment_2", "content": "{{ world.counter += 2; 'Incremented 2.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 20},
                {"id": "increment_3", "content": "{{ world.counter += 3; 'Incremented 3.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 30}
            ]
        }
    }
    return {"graph": graph_definition, "codices": codices_data}

@pytest.fixture
def codex_nonexistent_codex_data() -> dict:
    graph_definition = {
        "main": {"nodes": [{
            "id": "invoke_nonexistent",
            "run": [{"runtime": "system.invoke", "config": {"from": [{"codex": "nonexistent_codex"}]}}]
        }]}
    }
    # codices 是空的，因为我们就是想测试找不到的情况
    return {"graph": graph_definition, "codices": {}}