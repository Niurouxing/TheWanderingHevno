# tests/conftest_data.py

import pytest
from plugins.core_engine.contracts import GraphCollection

# --- Graph Fixtures ---

@pytest.fixture(scope="session")
def linear_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "A", "run": [{"runtime": "system.io.input", "config": {"value": "a story about a cat"}}]},
        {"id": "B", "run": [{"runtime": "llm.default", "config": {"model": "mock/model", "prompt": "{{ f'The story is: {nodes.A.output}' }}"}}]},
        {"id": "C", "run": [{"runtime": "llm.default", "config": {"model": "mock/model", "prompt": "{{ nodes.B.llm_output }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def parallel_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "source_A", "run": [{"runtime": "system.io.input", "config": {"value": "Value A"}}]},
        {"id": "source_B", "run": [{"runtime": "system.io.input", "config": {"value": "Value B"}}]},
        {"id": "merger", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Merged: {nodes.source_A.output} and {nodes.source_B.output}' }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def pipeline_collection() -> GraphCollection:
    # 已更新: world.main_character -> moment.main_character
    return GraphCollection.model_validate({"main": {"nodes": [{"id": "A", "run": [
        {"runtime": "system.execute", "config": {"code": "moment.main_character = 'Sir Reginald'"}},
        {"runtime": "system.io.input", "config": {"value": "A secret message"}},
        {"runtime": "llm.default", "config": {"model": "mock/model", "prompt": "{{ f'Tell a story about {moment.main_character}. He just received this message: {pipe.output}' }}"}}
    ]}]}})

@pytest.fixture(scope="session")
def world_vars_collection() -> GraphCollection:
    # 已更新: world.theme -> moment.theme
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "setter", "run": [{"runtime": "system.execute", "config": {"code": "moment.theme = 'cyberpunk'"}}]},
        {"id": "reader", "depends_on": ["setter"], "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'The theme is: {moment.theme}'}}"}}]}
    ]}})

@pytest.fixture(scope="session")
def execute_runtime_collection() -> GraphCollection:
    # 已更新: world.player_status -> moment.player_status
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "A_generate_code", "run": [{"runtime": "system.io.input", "config": {"value": "moment.player_status = 'empowered'"}}]},
        {"id": "B_execute_code", "run": [{"runtime": "system.execute", "config": {"code": "{{ nodes.A_generate_code.output }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def cyclic_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "A", "run": [{"runtime": "system.io.input", "config": {"value": "{{ nodes.C.output }}"}}]},
        {"id": "B", "run": [{"runtime": "system.io.input", "config": {"value": "{{ nodes.A.output }}"}}]},
        {"id": "C", "run": [{"runtime": "system.io.input", "config": {"value": "{{ nodes.B.output }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def failing_node_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "A_ok", "run": [{"runtime": "system.io.input", "config": {"value": "start"}}]},
        {"id": "B_fail", "run": [{"runtime": "system.io.input", "config": {"value": "{{ non_existent_variable }}"}}]},
        {"id": "C_skip", "run": [{"runtime": "system.io.input", "config": {"value": "{{ nodes.B_fail.output }}"}}]},
        {"id": "D_independent", "run": [{"runtime": "system.io.input", "config": {"value": "independent"}}]}
    ]}})

@pytest.fixture(scope="session")
def invalid_graph_no_main() -> dict:
    return {"not_main": {"nodes": [{"id": "a", "run": []}]}}

@pytest.fixture(scope="session")
def graph_evolution_collection() -> GraphCollection:
    # 已重构: 通过向 lore.graphs 写入来实现图的演化
    new_graph_dict = {"main": {"nodes": [{"id": "new_node", "run": [{"runtime": "system.io.input", "config": {"value": "This is the evolved graph!"}}]}]}}
    return GraphCollection.model_validate({"main": {"nodes": [{"id": "graph_generator", "run": [{
        "runtime": "system.execute",
        "config": {"code": f"lore.graphs = {new_graph_dict}"}
    }]}]}})

@pytest.fixture(scope="session")
def advanced_macro_collection() -> GraphCollection:
    # 【修复】将函数体作为字符串存入 lore，而不是将函数对象存入 moment。
    # 这样可以保证所有状态都是可序列化的。
    hypot_function_string = "import math\\ndef calculate_hypotenuse(a, b): return math.sqrt(a**2 + b**2)"

    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "teach_skill", "run": [{"runtime": "system.execute", "config": {
            "code": f"lore.math_utils_code = '{hypot_function_string}'"}}]},
        
        {"id": "use_skill", "depends_on": ["teach_skill"], "run": [{"runtime": "system.execute", "config": {
            "code": """
# 在执行上下文中动态定义函数
exec(lore.math_utils_code, globals())
# 调用刚刚定义的函数
return calculate_hypotenuse(3, 4)
"""}}]},
        
        {"id": "llm_propose_change", "run": [{"runtime": "system.io.input", "config": {"value": "moment.game_difficulty = 'hard'"}}]},
        {"id": "execute_change", "run": [{"runtime": "system.execute", "config": {"code": "{{ nodes.llm_propose_change.output }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def subgraph_call_collection() -> GraphCollection:
    # 已更新: world.global_setting -> moment.global_setting
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "data_provider", "run": [{"runtime": "system.io.input", "config": {"value": "Hello from main"}}]},
        {"id": "main_caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "process_item", "using": {"item_input": "{{ nodes.data_provider.output }}"}}}]}
    ]}, "process_item": {"nodes": [{"id": "processor", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Processed: {nodes.item_input.output} with world state: {moment.global_setting}' }}"}}]}]}})

@pytest.fixture(scope="session")
def nested_subgraph_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [{"id": "main_caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "sub1", "using": {"input_from_main": "level 0"}}}]}]},
        "sub1": {"nodes": [{"id": "sub1_caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "sub2", "using": {"input_from_sub1": "{{ nodes.input_from_main.output }}"}}}]}]},
        "sub2": {"nodes": [{"id": "final_processor", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Reached level 2 from: {nodes.input_from_sub1.output}' }}"}}]}]}})

@pytest.fixture(scope="session")
def subgraph_call_to_nonexistent_graph_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [{"id": "bad_caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "i_do_not_exist"}}]}]}})

@pytest.fixture(scope="session")
def subgraph_modifies_world_collection() -> GraphCollection:
    # 已更新: world.counter -> moment.counter
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "modifier", "using": {"amount": 10}}}]},
        {"id": "reader", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Final counter: {moment.counter}, Subgraph raw output: {nodes.caller.output}' }}"}}]}
    ]}, "modifier": {"nodes": [{"id": "incrementer", "run": [{"runtime": "system.execute", "config": {"code": "moment.counter += nodes.amount.output"}}]}]}})

@pytest.fixture(scope="session")
def subgraph_with_failure_collection() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "failing_subgraph"}}]},
        {"id": "downstream_of_fail", "run": [{"runtime": "system.io.input", "config": {"value": "{{ nodes.caller.output }}"}}]}
    ]}, "failing_subgraph": {"nodes": [
        {"id": "A_ok", "run": [{"runtime": "system.io.input", "config": {"value": "ok"}}]},
        {"id": "B_fail", "run": [{"runtime": "system.io.input", "config": {"value": "{{ non_existent.var }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def dynamic_subgraph_call_collection() -> GraphCollection:
    # 已更新: world.target_graph -> lore.target_graph (更符合逻辑)
    return GraphCollection.model_validate({"main": {"nodes": [{"id": "dynamic_caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "{{ lore.target_graph }}", "using": {"data": "dynamic data"}}}]}]},
        "sub_a": {"nodes": [{"id": "processor_a", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Processed by A: {nodes.data.output}' }}"}}]}]},
        "sub_b": {"nodes": [{"id": "processor_b", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Processed by B: {nodes.data.output}' }}"}}]}]}})

@pytest.fixture(scope="session")
def concurrent_write_collection() -> GraphCollection:
    # 已更新: world.counter -> moment.counter
    increment_code = "for i in range(100):\n    moment.counter += 1"
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "inc_A", "run": [{"runtime": "system.execute", "config": {"code": increment_code}}]},
        {"id": "inc_B", "run": [{"runtime": "system.execute", "config": {"code": increment_code}}]},
        {"id": "reader", "depends_on": ["inc_A", "inc_B"], "run": [{"runtime": "system.io.input", "config": {"value": "{{ moment.counter }}"}}]}
    ]}})

@pytest.fixture(scope="session")
def map_collection_basic() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "char_provider", "run": [{"runtime": "system.io.input", "config": {"value": ["Aragorn", "Gandalf"]}}]},
        {"id": "map_node", "run": [{"runtime": "system.flow.map", "config": {
            "list": "{{ nodes.char_provider.output }}",
            "graph": "process_character",
            "using": {"character_name": "{{ source.item }}"}
        }}]}
    ]}, "process_character": {"nodes": [{"id": "generate_bio", "run": [{"runtime": "system.io.input", "config": {"value": "{{ f'Bio for {nodes.character_name.output}' }}"}}]}]}})

@pytest.fixture(scope="session")
def map_collection_with_collect(map_collection_basic: GraphCollection) -> GraphCollection:
    base_data = map_collection_basic.model_dump()
    map_instruction = base_data["main"]["nodes"][1]["run"][0]
    map_instruction["config"]["collect"] = "{{ nodes.generate_bio.output }}"
    return GraphCollection.model_validate(base_data)

@pytest.fixture(scope="session")
def map_collection_concurrent_write() -> GraphCollection:
    # 已更新: world.gold -> moment.gold
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "task_provider", "run": [{"runtime": "system.io.input", "config": {"value": list(range(10))}}]},
        {"id": "concurrent_adder_map", "run": [{"runtime": "system.flow.map", "config": {"list": "{{ nodes.task_provider.output }}", "graph": "add_gold"}}]},
        {"id": "reader", "depends_on": ["concurrent_adder_map"], "run": [{"runtime": "system.io.input", "config": {"value": "{{ moment.gold }}"}}]}
    ]}, "add_gold": {"nodes": [{"id": "add_10_gold", "run": [{"runtime": "system.execute", "config": {"code": "moment.gold += 10"}}]}]}})

@pytest.fixture(scope="session")
def map_collection_with_failure() -> GraphCollection:
    return GraphCollection.model_validate({"main": {"nodes": [
        {"id": "data_provider", "run": [{"runtime": "system.io.input", "config": {"value": [{"name": "Alice"}, "Bob", {"name": "Charlie"}]}}]},
        {"id": "mapper", "run": [{"runtime": "system.flow.map", "config": {
            "list": "{{ nodes.data_provider.output }}",
            "graph": "process_name",
            "using": {"character_data": "{{ source.item }}"}
        }}]}
    ]}, "process_name": {"nodes": [{"id": "get_name", "run": [{"runtime": "system.io.input", "config": {"value": "{{ nodes.character_data.output.name }}"}}]}]}})


@pytest.fixture(scope="session")
def map_collection_with_collect_and_subgraph_node_ref() -> GraphCollection:
    return GraphCollection.model_validate({
        "main": { "nodes": [{"id": "mapper", "run": [{"runtime": "system.flow.map", "config": {
                            "list": ["apple", "banana"],
                            "graph": "process_with_index",
                            "using": {"fruit": "{{ source.item }}", "idx": "{{ source.index }}"},
                            "collect": "{{ nodes.processor.output }}" }}]}]
        },
        "process_with_index": {"nodes": [{"id": "processor", "run": [{"runtime": "system.io.input", "config": {
                        "value": "{{ f'Item: {nodes.fruit.output} at index {nodes.idx.output}' }}"}}]}]
        }})

@pytest.fixture(scope="session")
def call_collection_with_using_node_ref() -> GraphCollection:
    return GraphCollection.model_validate({
        "main": {"nodes": [{"id": "data_provider", "run": [{"runtime": "system.io.input", "config": {"value": "External Data"}}]},
                           {"id": "caller", "run": [{"runtime": "system.flow.call", "config": {"graph": "processor_graph", "using": {
                               "input_from_main": "{{ nodes.data_provider.output }}"}}}]}]},
        "processor_graph": {"nodes": [{"id": "processor", "run": [{"runtime": "system.io.input", "config": {
                        "value": "{{ f'Processed: {nodes.input_from_main.output}' }}"}}]}]
        }})


# --- Codex Data Fixtures (已全部重构) ---

@pytest.fixture(scope="session")
def codex_basic_data() -> dict:
    """已重构: 将 codices 放入 lore 作用域。"""
    return {
        "lore": {
            "graphs": {"main": {"nodes": [{"id": "invoke_test", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "info"}]}}]}]}},
            "codices": { "info": {"entries": [
                    {"id": "greeting", "content": "你好，冒险者！", "priority": 10},
                    {"id": "intro", "content": "欢迎来到这个奇幻的世界。", "priority": 5}
                ]}}
        },
        "moment": {}
    }

@pytest.fixture(scope="session")
def codex_keyword_and_priority_data() -> dict:
    """已重构: 将 codices 放入 lore 作用域。"""
    return {
        "lore": {
            "graphs": {"main": {"nodes": [
                {"id": "invoke_weather", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "weather", "source": "今天的魔法天气怎么样？"}]}}]},
                {"id": "invoke_mood", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "mood", "source": "我很开心。"}]}}]}
            ]}},
            "codices": {
                "weather": {"entries": [{"id": "magic", "content": "魔法能量活跃", "trigger_mode": "on_keyword", "keywords": ["魔法天气"], "priority": 30}]},
                "mood": {"entries": [{"id": "happy", "content": "你很高兴", "trigger_mode": "on_keyword", "keywords": ["开心"], "priority": 5}]}
            }
        },
        "moment": {}
    }

@pytest.fixture(scope="session")
def codex_macro_eval_data() -> dict:
    """已重构: 将静态 codex 放入 lore，动态状态放入 moment。"""
    return {
        "lore": {
            "graphs": {"main": {"nodes": [{"id": "get_report", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "dynamic", "source": "告诉我关于秘密"}]}}]}]}},
            "codices": {"dynamic": {"entries": [
                {"id": "night_info", "content": "现在是夜晚", "is_enabled": "{{ moment.is_night }}"},
                {"id": "secret_info", "content": "你提到了秘密", "trigger_mode": "on_keyword", "keywords": "{{ [moment.hidden_keyword] }}"}
            ]}}
        },
        "moment": {
            "is_night": True,
            "hidden_keyword": "秘密"
        }
    }

@pytest.fixture(scope="session")
def codex_recursion_data() -> dict:
    """已重构: 将 codices 放入 lore 作用域。"""
    return {
        "lore": {
            "graphs": {"main": {"nodes": [{"id": "recursive_invoke", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "lore", "source": "A"}], "recursion_enabled": True}}]}]}},
            "codices": {"lore": {"entries": [
                {"id": "entry_A", "content": "这是关于A的信息，它引出B。", "trigger_mode": "on_keyword", "keywords": ["A"], "priority": 10},
                {"id": "entry_B", "content": "B被A触发了，它又引出C。", "trigger_mode": "on_keyword", "keywords": ["B"], "priority": 20},
                {"id": "entry_C", "content": "C被B触发了，这是最终信息。", "trigger_mode": "on_keyword", "keywords": ["C"], "priority": 30},
                {"id": "entry_D_always_on", "content": "这是一个总是存在的背景信息。", "trigger_mode": "always_on", "priority": 5}
            ]}}
        },
        "moment": {}
    }

@pytest.fixture(scope="session")
def codex_concurrent_world_write_data() -> dict:
    """已重构: 将 codices 放入 lore, counter 放入 moment。"""
    return {
        "lore": {
            "graphs": {"main": {"nodes": [
                {"id": "invoke", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "concurrent_codex", "source": "触发计数"}]}}]},
                {"id": "reader", "depends_on": ["invoke"], "run": [{"runtime": "system.io.input", "config": {"value": "{{ moment.counter }}"}}]}
            ]}},
            "codices": {"concurrent_codex": {"entries": [
                {"id": "increment_1", "content": "{{ moment.counter += 1; 'Incremented 1.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 10},
                {"id": "increment_2", "content": "{{ moment.counter += 2; 'Incremented 2.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 20},
                {"id": "increment_3", "content": "{{ moment.counter += 3; 'Incremented 3.' }}", "trigger_mode": "on_keyword", "keywords": ["计数"], "priority": 30}
            ]}}
        },
        "moment": {
            "counter": 0
        }
    }

@pytest.fixture(scope="session")
def codex_nonexistent_codex_data() -> dict:
    """已重构: 将 codices 放入 lore 作用域。"""
    return {
        "lore": {
            "graphs": {"main": {"nodes": [{"id": "invoke_nonexistent", "run": [{"runtime": "codex.invoke", "config": {"from": [{"codex": "nonexistent_codex"}]}}]}]}},
            "codices": {}
        },
        "moment": {}
    }