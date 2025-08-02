# conftest.py
import pytest
import asyncio
from typing import Generator, List
from fastapi import FastAPI
# 导入 ASGITransport 以包装我们的 app
from httpx import AsyncClient, ASGITransport

# 从平台核心导入
from backend.app import create_app
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader

# --- 核心 Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """为整个测试会话创建一个事件循环。"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def clean_container() -> Container:
    """提供一个全新的、空的 DI 容器实例。"""
    return Container()

@pytest.fixture
def hook_manager() -> HookManager:
    """提供一个全新的、空的 HookManager 实例。"""
    return HookManager()

# --- 插件加载 Fixtures ---

class TestPluginLoader(PluginLoader):
    """一个特殊的插件加载器，可以按需加载指定的插件。"""
    def __init__(self, container: Container, hook_manager: HookManager, enabled_plugins: List[str]):
        super().__init__(container, hook_manager)
        self.enabled_plugins = enabled_plugins

    def _discover_plugins(self) -> List[dict]:
        """重写发现逻辑，只“发现”被启用的插件。"""
        all_plugins = super()._discover_plugins()
        print(f"TestPluginLoader: Found {len(all_plugins)} total plugins, filtering for {self.enabled_plugins}")
        enabled = [p for p in all_plugins if p['name'] in self.enabled_plugins]
        print(f"TestPluginLoader: Enabled {len(enabled)} plugins.")
        return enabled

@pytest.fixture
def loaded_plugins(
    clean_container: Container,
    hook_manager: HookManager
) -> Generator[None, List[str], None]:
    """
    一个【生成器 fixture】，允许测试按需加载一组特定的插件。
    """
    _loader = None
    
    def _load(plugin_names: List[str]):
        nonlocal _loader
        _loader = TestPluginLoader(clean_container, hook_manager, enabled_plugins=plugin_names)
        _loader.load_plugins()

    yield _load
    
    print("Plugin loading fixture teardown.")


# --- 应用与客户端 Fixtures ---

@pytest.fixture
async def test_app(
    loaded_plugins: Generator[None, List[str], None]
) -> Generator[FastAPI, List[str], None]:
    """
    一个更高阶的 fixture，它创建一个 FastAPI 应用实例，并加载指定的插件。
    """
    app_instance = None
    
    async def _create(plugin_names: List[str]):
        nonlocal app_instance
        
        if "core-logging" not in plugin_names:
            plugin_names.insert(0, "core-logging")

        app_instance = create_app()

        container = Container()
        hook_manager = HookManager()

        loader = TestPluginLoader(container, hook_manager, enabled_plugins=plugin_names)
        loader.load_plugins()

        app_instance.state.container = container
        app_instance.state.hook_manager = hook_manager

        routers_to_add = await hook_manager.filter("collect_api_routers", [])
        for router in routers_to_add:
            app_instance.include_router(router)
        
        return app_instance

    yield _create

@pytest.fixture
async def async_client(test_app: Generator[FastAPI, List[str], None]) -> Generator[AsyncClient, List[str], None]:
    """
    一个终极测试客户端 fixture。
    它接收一个插件列表，构建一个只包含这些插件的应用，并返回一个可以对其进行 HTTP 请求的客户端。
    """
    client_instance = None
    
    async def _create_client(plugin_names: List[str]):
        nonlocal client_instance
        app = await test_app(plugin_names)
        
        # --- 核心修复：使用 ASGITransport 来包装 app ---
        transport = ASGITransport(app=app)
        client_instance = AsyncClient(transport=transport, base_url="http://test")
        
        return client_instance

    yield _create_client
    
    if client_instance:
        await client_instance.aclose()