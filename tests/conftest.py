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