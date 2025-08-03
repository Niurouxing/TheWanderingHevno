# tests/conftest.py
import os
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from typing import Generator, AsyncGenerator, Tuple

# 1. 应用工厂和核心组件导入
from backend.app import create_app
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.tasks import BackgroundTaskManager

# 2. 插件注册函数导入
from plugins.core_engine import register_plugin as register_engine_plugin, populate_runtime_registry
from plugins.core_llm import register_plugin as register_llm_plugin
from plugins.core_codex import register_plugin as register_codex_plugin
from plugins.core_persistence import register_plugin as register_persistence_plugin
from plugins.core_api import register_plugin as register_api_plugin
from plugins.core_logging import register_plugin as register_logging_plugin

# 3. 契约和数据模型导入
from backend.core.contracts import Container as ContainerInterface, HookManager as HookManagerInterface
from plugins.core_engine.contracts import ExecutionEngineInterface, SnapshotStoreInterface

# 4. 使用 pytest_plugins 加载所有共享的数据 fixture
pytest_plugins = "tests.conftest_data"


# --- App/E2E Level Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """为整个测试会话设置环境变量。"""
    os.environ["HEVNO_LLM_DEBUG_MODE"] = "true"
    os.environ["HEVNO_ASSETS_DIR"] = "test_assets" # 为测试持久化插件设置一个隔离的目录
    yield
    # 清理
    if os.path.exists("test_assets"):
        import shutil
        shutil.rmtree("test_assets")

@pytest.fixture(scope="session")
def app() -> Generator[TestClient, None, None]:
    """创建完整的 FastAPI 应用实例，用于 E2E 测试。"""
    yield create_app()

@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    """为每个 E2E 测试提供一个干净的 TestClient 和状态。"""
    with TestClient(app) as client:
        container = client.app.state.container
        sandbox_store: dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        sandbox_store.clear()
        snapshot_store.clear()
        yield client


# --- Integration-Level Fixtures ---

@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface], None]:
    """
    【全局共享】为跨插件集成测试提供一个功能齐全的 ExecutionEngine 实例。
    """
    container = Container()
    hook_manager = HookManager()
    task_manager = BackgroundTaskManager(container, max_workers=2)

    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)
    container.register("task_manager", lambda: task_manager, singleton=True)
    
    # 手动加载所有核心插件，以模拟一个完整的运行环境
    register_logging_plugin(container, hook_manager)
    register_persistence_plugin(container, hook_manager)
    register_engine_plugin(container, hook_manager)
    register_llm_plugin(container, hook_manager)
    register_codex_plugin(container, hook_manager)
    register_api_plugin(container, hook_manager)


    # 手动触发异步钩子来填充服务
    await container.resolve("hook_manager").trigger("services_post_register", container=container)

    engine = container.resolve("execution_engine")
    
    task_manager.start()
    yield engine, container, hook_manager
    await task_manager.stop()