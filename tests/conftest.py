# tests/conftest.py

import pytest
import asyncio
from typing import Tuple, Dict, Any, Callable
from uuid import UUID

from fastapi import FastAPI
from httpx import AsyncClient
from fastapi.testclient import TestClient

# 平台核心
from backend.app import create_app
from backend.core.contracts import Container, HookManager, BackgroundTaskManager

# 核心插件契约与服务
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionEngineInterface, 
    SnapshotStoreInterface,
    GraphCollection
)
from plugins.core_persistence.stores import PersistentSandboxStore, PersistentSnapshotStore
from plugins.core_engine.contracts import SandboxStoreInterface, SnapshotStoreInterface

# --- 1. 基础应用与客户端 Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """为所有异步测试创建一个事件循环。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

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

@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """
    【用于异步 API 测试 (推荐)】
    提供一个 function 级别的、支持异步操作的 HTTPX AsyncClient。
    这是进行端到端（E2E）API 测试的首选。
    """
    # --- 核心修复 ---
    # httpx.AsyncClient 需要一个 transport 参数来与 ASGI 应用通信，
    # 而不是 app 参数。
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
# --- 2. 核心服务与引擎 Fixtures (用于集成测试) ---

@pytest.fixture(scope="function")
def test_engine_setup(test_client: TestClient) -> Tuple[ExecutionEngineInterface, Container, HookManager]:
    """
    【集成测试基础】
    为引擎的集成测试提供核心组件。
    它从 session 级别的应用中获取服务，确保测试运行在完全配置的环境中。
    在每次测试前，它会清理存储的缓存，以确保测试隔离性。
    
    返回:
        - ExecutionEngineInterface: 已配置的执行引擎实例。
        - Container: DI 容器。
        - HookManager: 钩子管理器。
    """
    container: Container = test_client.app.state.container
    
    # 获取核心服务
    engine: ExecutionEngineInterface = container.resolve("execution_engine")
    hook_manager: HookManager = container.resolve("hook_manager")
    sandbox_store: SandboxStoreInterface = container.resolve("sandbox_store")
    snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

    # --- 关键：测试隔离 ---
    # 在每次测试函数执行前，清空内存缓存。
    # 注意：这不会删除磁盘上的文件，但能确保测试不会从上一个测试的缓存中读取到旧数据。
    # 这是对持久化存储进行快速集成测试的一种折衷。
    sandbox_store._cache.clear()
    snapshot_store._cache.clear()
    
    yield engine, container, hook_manager

    # 测试后清理（可选，但良好实践）
    sandbox_store._cache.clear()
    snapshot_store._cache.clear()


@pytest.fixture(scope="function")
def sandbox_factory(
    test_engine_setup: Tuple[ExecutionEngineInterface, Container, HookManager]
) -> Callable[..., Sandbox]:
    """
    【集成测试主力】
    提供一个工厂函数，用于为集成测试创建、持久化并返回一个完整的 Sandbox 实例。
    这极大地简化了测试用例的 Arrange 阶段。
    
    使用示例:
    sandbox = sandbox_factory(graph_collection=my_graph, initial_moment={"hp": 100})
    """
    _, container, _ = test_engine_setup
    sandbox_store: SandboxStoreInterface = container.resolve("sandbox_store")
    snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

    # 使用 async def 定义内部工厂，因为它需要调用异步的 .save() 方法
    async def _sandbox_factory(
        graph_collection: GraphCollection,
        initial_lore: Dict[str, Any] = None,
        initial_moment: Dict[str, Any] = None,
        sandbox_name: str = "Test Sandbox"
    ) -> Sandbox:
        """
        工厂函数本身。
        """
        # 准备状态
        _initial_lore = initial_lore if initial_lore is not None else {}
        _initial_moment = initial_moment if initial_moment is not None else {}
        
        # 将图定义合并到 lore 中
        _initial_lore["graphs"] = graph_collection.model_dump()

        # 创建沙盒
        sandbox = Sandbox(
            name=sandbox_name,
            definition={
                "initial_lore": _initial_lore,
                "initial_moment": _initial_moment
            },
            lore=_initial_lore
        )

        # 创建创世快照
        genesis_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            moment=_initial_moment
        )
        
        # 链接沙盒与创世快照
        sandbox.head_snapshot_id = genesis_snapshot.id
        
        # --- 关键：模拟持久化 ---
        # 将创建的对象保存到存储中，以便引擎可以找到它们
        await snapshot_store.save(genesis_snapshot)
        await sandbox_store.save(sandbox)
        
        return sandbox

    return _sandbox_factory


# --- 3. 端到端 API 测试 Fixtures ---

@pytest.fixture
async def sandbox_in_db(client: AsyncClient, linear_collection: GraphCollection) -> Sandbox:
    """
    【端到端测试主力】
    通过 API 创建一个沙盒，并确保在测试结束后通过 API 将其删除。
    这为 API 测试提供了完美的隔离性。
    
    返回:
        - Sandbox: 一个通过 API 创建并存在于应用状态中的完整沙盒对象。
    """
    # 1. Arrange: 通过 API 创建沙盒
    create_request_body = {
        "name": "E2E Test Sandbox",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump()},
            "initial_moment": {"player_name": "E2E_Tester"}
        }
    }
    response = await client.post("/api/sandboxes", json=create_request_body)
    assert response.status_code == 201, f"Failed to create sandbox for E2E test: {response.text}"
    
    sandbox_data = response.json()
    sandbox = Sandbox.model_validate(sandbox_data)

    # 2. Yield: 将创建好的沙盒对象提供给测试用例
    yield sandbox

    # 3. Teardown: 测试结束后，通过 API 删除沙盒
    delete_response = await client.delete(f"/api/sandboxes/{sandbox.id}")
    assert delete_response.status_code in [204, 404], "Failed to clean up sandbox after E2E test."