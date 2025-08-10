# tests/conftest.py

import pytest
import asyncio
from typing import Tuple, Dict, Any, Callable, AsyncGenerator

from fastapi import FastAPI
from httpx import AsyncClient
from httpx import ASGITransport 
from fastapi.testclient import TestClient
from asgi_lifespan import LifespanManager 

from tests.conftest_data import *

# 平台核心
# 【修改】从 backend.main 导入 app，而不是自己调用 create_app()
# 这样可以确保我们测试的是与手动运行完全相同的实例
from backend.main import app as main_app 

from backend.core.contracts import Container, HookManager
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionEngineInterface, 
    GraphCollection
)
# 【修改】从 core_engine 导入存储接口，这是它们现在所属的位置
from plugins.core_engine.contracts import SandboxStoreInterface, SnapshotStoreInterface

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """
    创建一个 session 级别的 FastAPI 应用实例。
    这将触发应用的完整启动生命周期（lifespan），包括插件加载和服务注册。
    只执行一次，以提高测试速度。
    """
    return create_app()

@pytest.fixture(scope="session")
def test_client(app: FastAPI) -> TestClient:
    """
    【用于同步 API 测试】
    提供一个 session 级别的、传统的 FastAPI TestClient。
    注意：在新的异步 API 中，推荐使用下面的 AsyncClient。
    """
    with TestClient(app) as client:
        yield client



# --- 1. 基础应用与客户端 Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """为所有异步测试创建一个事件循环。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    【最终修复】
    一个用于端到端测试的、正确处理应用生命周期的 AsyncClient fixture。
    这个 fixture 会在整个测试会ভিশн中只启动一次应用。
    """
    async with LifespanManager(main_app) as manager:
        # 1. LifespanManager 包装应用以处理启动/关闭事件。
        # 2. 我们为包装后的应用 manager.app 创建一个 ASGITransport。
        transport = ASGITransport(app=manager.app)
        # 3. 将 transport 传递给 AsyncClient。
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# --- 2. 核心服务与引擎 Fixtures (用于集成测试) ---

@pytest.fixture(autouse=True)
def force_llm_debug_mode(monkeypatch):
    """在所有 engine 测试运行期间，自动设置环境变量，强制使用 MockLLMService。"""
    monkeypatch.setenv("HEVNO_LLM_DEBUG_MODE", "true")


@pytest.fixture(scope="function")
def test_engine_setup(client: AsyncClient) -> Tuple[ExecutionEngineInterface, Container, HookManager]:
    """
    【集成测试基础】
    为引擎的集成测试提供核心组件。
    它从 session 级别的应用中获取服务，确保测试运行在完全配置的环境中。
    在每次测试前，它会清理存储的缓存，以确保测试隔离性。
    """
    # 【最终修复】: 直接从导入的 main_app 访问 state。
    # 因为 client fixture (session-scoped) 已经确保了 main_app 的 lifespan 启动事件被触发。
    container: Container = main_app.state.container
    
    # 获取核心服务
    engine: ExecutionEngineInterface = container.resolve("execution_engine")
    hook_manager: HookManager = container.resolve("hook_manager")
    sandbox_store: SandboxStoreInterface = container.resolve("sandbox_store")
    snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

    # --- 关键：测试隔离 ---
    if hasattr(sandbox_store, '_cache'):
        sandbox_store._cache.clear() # type: ignore
    if hasattr(snapshot_store, '_cache'):
        snapshot_store._cache.clear() # type: ignore
    
    yield engine, container, hook_manager

    # 测试后清理
    if hasattr(sandbox_store, '_cache'):
        sandbox_store._cache.clear() # type: ignore
    if hasattr(snapshot_store, '_cache'):
        snapshot_store._cache.clear() # type: ignore


@pytest.fixture(scope="function")
def sandbox_factory(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager]
) -> Callable[..., Sandbox]:
    """
    【集成测试主力】
    提供一个工厂函数，用于为集成测试创建、持久化并返回一个完整的 Sandbox 实例。
    """
    _, container, _ = test_engine_setup
    sandbox_store: SandboxStoreInterface = container.resolve("sandbox_store")
    snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

    async def _sandbox_factory(
        graph_collection: GraphCollection,
        initial_lore: Dict[str, Any] = None,
        initial_moment: Dict[str, Any] = None,
        sandbox_name: str = "Test Sandbox"
    ) -> Sandbox:
        _initial_lore = initial_lore if initial_lore is not None else {}
        _initial_moment = initial_moment if initial_moment is not None else {}
        
        # 将图定义合并到 lore 中
        if "graphs" not in _initial_lore:
            _initial_lore["graphs"] = {}
        _initial_lore["graphs"].update(graph_collection.model_dump(mode='json'))

        sandbox = Sandbox(
            name=sandbox_name,
            definition={"initial_lore": _initial_lore, "initial_moment": _initial_moment},
            lore=_initial_lore
        )

        genesis_snapshot = StateSnapshot(sandbox_id=sandbox.id, moment=_initial_moment)
        sandbox.head_snapshot_id = genesis_snapshot.id
        
        await snapshot_store.save(genesis_snapshot)
        await sandbox_store.save(sandbox)
        
        return sandbox

    return _sandbox_factory


@pytest.fixture
def codex_sandbox_factory(sandbox_factory: callable) -> callable:
    """
    一个便利的包装器，将通用的 sandbox_factory 和 codex 测试数据结合起来。
    """
    async def _create_codex_sandbox(codex_data: dict):
        # 导入需要的模型
        from plugins.core_engine.contracts import Sandbox, GraphCollection

        # 从 codex_data 中分离出图、lore 和 moment
        graph_collection_dict = codex_data.get("lore", {}).get("graphs", {})
        initial_lore = codex_data.get("lore", {})
        initial_moment = codex_data.get("moment", {})
        
        # 从 lore 数据中移除 'graphs'，因为它会被自动添加
        if 'graphs' in initial_lore:
            # 使用副本以避免修改原始fixture数据
            initial_lore = initial_lore.copy()
            del initial_lore['graphs']
            
        graph_collection_obj = GraphCollection.model_validate(graph_collection_dict)

        # 调用父工厂 (sandbox_factory 是通过 pytest_plugins 注入的)
        sandbox: Sandbox = await sandbox_factory(
            graph_collection=graph_collection_obj,
            initial_lore=initial_lore,
            initial_moment=initial_moment
        )
        return sandbox
    return _create_codex_sandbox

# --- 3. 端到端 API 测试 Fixtures ---

@pytest.fixture
async def sandbox_in_db(client: AsyncClient, linear_collection: GraphCollection) -> AsyncGenerator[Sandbox, None]:
    """
    【端到端测试主力】
    通过 API 创建一个沙盒，并确保在测试结束后通过 API 将其删除。
    """
    create_request_body = {
        "name": "E2E Test Sandbox",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump(mode='json')},
            "initial_moment": {"player_name": "E2E_Tester"}
        }
    }
    response = await client.post("/api/sandboxes", json=create_request_body)
    assert response.status_code == 201, f"Failed to create sandbox for E2E test: {response.text}"
    
    sandbox = Sandbox.model_validate(response.json())

    yield sandbox

    delete_response = await client.delete(f"/api/sandboxes/{sandbox.id}")
    assert delete_response.status_code in [204, 404], "Failed to clean up sandbox after E2E test."