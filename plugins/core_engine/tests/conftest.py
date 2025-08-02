# plugins/core_engine/tests/conftest.py

import pytest
import asyncio
from typing import Generator

# 从平台核心导入
from backend.container import Container
from backend.core.hooks import HookManager

# 从本插件导入
from plugins.core_engine.engine import ExecutionEngine
from plugins.core_engine.registry import RuntimeRegistry
from plugins.core_engine.state import SnapshotStore
from plugins.core_engine.runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from plugins.core_engine.runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

# 从其他插件导入，但我们只导入它们的注册函数或 Mock
from plugins.core_llm import register_plugin as register_llm_plugin
from plugins.core_codex import register_plugin as register_codex_plugin


@pytest.fixture
def test_engine() -> Generator[ExecutionEngine, None, None]:
    """
    为引擎集成测试提供一个完全配置好的 ExecutionEngine 实例。
    这个 fixture 模拟了应用启动时的插件加载和服务装配过程。
    """
    # 1. 创建平台核心服务
    container = Container()
    hook_manager = HookManager()

    # 2. 手动注册 core_engine 自身的服务
    container.register("snapshot_store", lambda: SnapshotStore(), singleton=True)
    container.register("sandbox_store", lambda: {}, singleton=True)
    
    # 注册一个空的 RuntimeRegistry，稍后通过钩子填充
    runtime_registry = RuntimeRegistry()
    container.register("runtime_registry", lambda: runtime_registry)
    
    # 注册引擎，它依赖于上面注册的服务
    engine_factory = lambda c: ExecutionEngine(
        registry=c.resolve("runtime_registry"),
        container=c,
        hook_manager=hook_manager
    )
    container.register("execution_engine", engine_factory, singleton=True)

    # 3. 手动注册 core_engine 自己的运行时 (这些是内置的)
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
    runtime_registry.register("system.execute", ExecuteRuntime)
    runtime_registry.register("system.call", CallRuntime)
    runtime_registry.register("system.map", MapRuntime)

    # 4. 手动注册依赖插件 (core_llm, core_codex) 的钩子
    #    这会向 hook_manager 添加 'collect_runtimes' 的实现
    register_llm_plugin(container, hook_manager)
    register_codex_plugin(container, hook_manager)

    # 5. 手动触发异步钩子来填充 RuntimeRegistry
    async def populate_runtimes():
        external_runtimes = await hook_manager.filter("collect_runtimes", {})
        for name, runtime_class in external_runtimes.items():
            runtime_registry.register(name, runtime_class)

    asyncio.run(populate_runtimes())

    # 6. 从容器中解析出最终配置好的引擎实例
    engine = container.resolve("execution_engine")
    yield engine