# tests/conftest.py
import json
import pytest
from fastapi.testclient import TestClient
from typing import Generator

# ---------------------------------------------------------------------------
# 从你的应用代码中导入核心类和函数
# ---------------------------------------------------------------------------
# 确保你的项目结构允许从 tests/ 目录导入 backend/
# 这通常需要项目根目录有一个 __init__.py 文件，或者通过 pytest 的配置来设置 python-path。
# 为了简单起见，我们假设可以直接导入。
from backend.main import app, setup_application, sandbox_store, snapshot_store
from backend.models import GraphCollection
from backend.core.registry import RuntimeRegistry
from backend.core.engine import ExecutionEngine
from backend.runtimes.base_runtimes import (
    InputRuntime, TemplateRuntime, LLMRuntime, SetWorldVariableRuntime
)


# ---------------------------------------------------------------------------
# Fixtures for Core Components (Engine, Registry, API Client)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def populated_registry() -> RuntimeRegistry:
    """
    提供一个预先填充了所有基础运行时的注册表实例。
    使用 'session' 作用域，因为注册表在所有测试中都是一样的，只需创建一次。
    """
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("system.template", TemplateRuntime)
    registry.register("llm.default", LLMRuntime)
    registry.register("system.set_world_var", SetWorldVariableRuntime)
    # 当添加 map/call 运行时后，在这里注册它们
    # registry.register("system.map", MapRuntime)
    # registry.register("system.call", CallRuntime)
    print("\n--- Populated Registry Created (Session Scope) ---")
    return registry


@pytest.fixture(scope="function")
def test_engine(populated_registry: RuntimeRegistry) -> ExecutionEngine:
    """
    提供一个配置了标准运行时的 ExecutionEngine 实例。
    使用 'function' 作用域，确保每个测试函数都获得一个干净的引擎实例。
    """
    return ExecutionEngine(registry=populated_registry)


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """
    提供一个 FastAPI TestClient 用于端到端 API 测试。
    使用 'session' 作用域以避免为每个测试重新启动应用。
    使用 yield 来确保在测试会话结束后执行清理代码。
    """
    # 清理全局存储，以确保测试会话之间的隔离
    sandbox_store.clear()
    snapshot_store.clear()
    
    # 使用 TestClient
    with TestClient(app) as client:
        print("\n--- TestClient Created (Session Scope) ---")
        yield client
    
    # (可选) 在所有测试完成后执行清理
    print("\n--- TestClient Teardown ---")
    sandbox_store.clear()
    snapshot_store.clear()


# ---------------------------------------------------------------------------
# Fixtures for Graph Collections (Test Data)
# ---------------------------------------------------------------------------

# --- 基本流程 ---

@pytest.fixture
def linear_collection() -> GraphCollection:
    """一个简单的三节点线性图：A -> B -> C，通过宏隐式依赖。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A", "data": {"runtime": "system.input", "value": "a story about a cat"}},
                {"id": "B", "data": {"runtime": "system.template", "template": "The story is: {{ nodes.A.output }}"}},
                {"id": "C", "data": {"runtime": "llm.default", "prompt": "{{ nodes.B.output }}"}}
            ]
        }
    })


@pytest.fixture
def parallel_collection() -> GraphCollection:
    """一个扇出再扇入的图，测试并行执行。 (A, B) -> C"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "source_A", "data": {"runtime": "system.input", "value": "Value A"}},
                {"id": "source_B", "data": {"runtime": "system.input", "value": "Value B"}},
                {"id": "merger", "data": {
                    "runtime": "system.template",
                    "template": "Merged: {{ nodes.source_A.output }} and {{ nodes.source_B.output }}"
                }}
            ]
        }
    })


@pytest.fixture
def pipeline_collection() -> GraphCollection:
    """一个包含节点内运行时管道的图。 A -> B(template | llm)"""
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


# --- 状态管理 ---

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
                {"id": "reader", "data": {
                    "runtime": "system.template",
                    "template": "The theme is: {{ world.theme }}"
                }}
            ]
        }
    })


@pytest.fixture
def graph_evolution_collection() -> GraphCollection:
    """
    一个用于测试图演化的特殊图。
    它会生成一个新的 GraphCollection 定义并将其存储在 world_state 中。
    """
    # 这是新图的定义，我们用 JSON 字符串来表示它，因为节点需要生成它。
    # 1. 定义新图为 Python 字典
    new_graph_dict = {
      "main": {
        "nodes": [
          { "id": "new_node", "data": { "runtime": "system.input", "value": "This is the evolved graph!" } }
        ]
      }
    }
    # 2. 使用 json.dumps 将其序列化为紧凑的 JSON 字符串
    new_graph_json_string = json.dumps(new_graph_dict)
    
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {
                    "id": "graph_generator",
                    "data": {
                        "runtime": "system.set_world_var",
                        "variable_name": "__graph_collection__",
                        # 3. 使用序列化后的字符串
                        "value": new_graph_json_string
                    }
                }
            ]
        }
    })


# --- 错误与边界情况 ---

@pytest.fixture
def cyclic_collection() -> GraphCollection:
    """一个包含环路的图，用于测试环路检测。 A -> B -> C -> A"""
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
def failing_node_collection() -> GraphCollection:
    """一个包含注定会失败的节点的图，用于测试错误处理和下游跳过。"""
    return GraphCollection.model_validate({
        "main": {
            "nodes": [
                {"id": "A_ok", "data": {"runtime": "system.input", "value": "start"}},
                # 节点 B 会因为引用未定义的变量而失败
                {"id": "B_fail", "data": {"runtime": "system.template", "template": "{{ undefined.var }}"}},
                # 节点 C 依赖于失败的节点 B，应该被跳过
                {"id": "C_skip", "data": {"runtime": "system.template", "template": "Value: {{ nodes.B_fail.output }}"}},
                # 节点 D 不依赖于失败的分支，应该成功执行
                {"id": "D_independent", "data": {"runtime": "system.input", "value": "independent"}}
            ]
        }
    })


@pytest.fixture
def invalid_graph_no_main() -> dict:
    """一个无效的图定义，缺少 'main' 入口点。用于 API 测试。"""
    return {
      "not_main": {
        "nodes": [
          {"id": "a", "data": {"runtime": "test"}}
        ]
      }
    }