# ./conftest.py
import os
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from typing import Generator, AsyncGenerator, Tuple, Callable, Dict, Any, Optional
from uuid import uuid4

# 1. 应用工厂和核心组件导入
from backend.app import create_app
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.tasks import BackgroundTaskManager

# 2. 插件注册函数导入 (保持不变)
from plugins.core_engine import register_plugin as register_engine_plugin
from plugins.core_llm import register_plugin as register_llm_plugin
from plugins.core_codex import register_plugin as register_codex_plugin
from plugins.core_persistence import register_plugin as register_persistence_plugin
from plugins.core_api import register_plugin as register_api_plugin
from plugins.core_logging import register_plugin as register_logging_plugin

# 3. 契约和数据模型导入 (进行适配)
from backend.core.contracts import Container as ContainerInterface, HookManager as HookManagerInterface
from plugins.core_engine.contracts import (
    ExecutionEngineInterface, 
    SnapshotStoreInterface,
    Sandbox,          
    StateSnapshot,   
    GraphCollection  
)

# 4. 使用 pytest_plugins 加载所有共享的数据 fixture (保持不变)
pytest_plugins = "tests.conftest_data"


# --- App/E2E Level Fixtures (保持不变) ---

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """为整个测试会话设置环境变量。"""
    os.environ["HEVNO_LLM_DEBUG_MODE"] = "true"
    os.environ["HEVNO_ASSETS_DIR"] = "test_assets"
    yield
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


# --- Integration-Level Fixtures (进行重构) ---

@pytest_asyncio.fixture
async def test_engine_setup() -> AsyncGenerator[Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface], None]:
    """
    【已重命名和调整】
    为集成测试提供一个功能齐全的引擎和容器环境。
    这个 fixture 现在只负责组装核心服务，不处理具体的沙盒状态。
    """
    container = Container()
    hook_manager = HookManager(container)
    task_manager = BackgroundTaskManager(container, max_workers=2)

    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)
    container.register("task_manager", lambda: task_manager, singleton=True)
    
    # 手动加载所有核心插件
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


@pytest.fixture
def sandbox_factory(
    test_engine_setup: Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface]
) -> Callable[..., Sandbox]:
    """
    【全新的核心 Fixture】
    一个工厂函数，用于创建和初始化一个完整的、可供测试的沙盒。
    它封装了新架构下所有必需的设置步骤。
    """
    _, container, _ = test_engine_setup
    
    def _create_sandbox(
        graph_collection: GraphCollection,
        initial_lore: Optional[Dict[str, Any]] = None,
        initial_moment: Optional[Dict[str, Any]] = None,
        definition: Optional[Dict[str, Any]] = None
    ) -> Sandbox:
        """
        内部工厂函数。
        :param graph_collection: 测试要使用的图。
        :param initial_lore: Lore 作用域的初始状态。
        :param initial_moment: Moment 作用域的初始状态。
        :param definition: 沙盒的 Definition，如果未提供则自动生成。
        :return: 一个完全初始化的 Sandbox 实例。
        """
        sandbox_id = uuid4()
        
        # 确保字典不为 None
        lore_data = initial_lore or {}
        moment_data = initial_moment or {}

        # 将图定义自动放入 Lore 中
        lore_data['graphs'] = graph_collection.model_dump()

        # 如果未提供 definition，则根据初始状态自动创建
        if definition is None:
            definition = {
                "initial_lore": lore_data,
                "initial_moment": moment_data
            }

        # 1. 创建 Sandbox 实例
        sandbox = Sandbox(
            id=sandbox_id,
            name="Test Sandbox",
            definition=definition,
            lore=lore_data,
        )

        # 2. 创建创世快照
        genesis_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            moment=moment_data
        )

        # 3. 链接快照并保存
        sandbox.head_snapshot_id = genesis_snapshot.id
        
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        snapshot_store.save(genesis_snapshot)
        
        # 4. 将沙盒存入内存存储中，以便引擎可以找到它
        sandbox_store: Dict[uuid4, Sandbox] = container.resolve("sandbox_store")
        sandbox_store[sandbox.id] = sandbox

        return sandbox

    return _create_sandbox