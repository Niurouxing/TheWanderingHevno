# plugins/core_memoria/tests/conftest.py (已重构)

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Tuple, Callable, Dict, Any, Optional
from uuid import uuid4

# 从平台核心导入
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.tasks import BackgroundTaskManager
from backend.core.contracts import Container as ContainerInterface, HookManager as HookManagerInterface

# 从依赖插件导入
from plugins.core_engine.contracts import (
    ExecutionEngineInterface, 
    SnapshotStoreInterface,
    Sandbox,          
    StateSnapshot,   
    GraphCollection,
)
from plugins.core_engine import register_plugin as register_engine_plugin
from plugins.core_llm import register_plugin as register_llm_plugin

# 从当前插件导入
from .. import register_plugin as register_memoria_plugin

@pytest_asyncio.fixture
async def memoria_test_setup() -> AsyncGenerator[Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface], None]:
    """
    【已重命名】
    为 core_memoria 插件的集成测试提供一个隔离的引擎环境。
    它只加载运行 memoria 功能所必需的插件。
    """
    container = Container()
    hook_manager = HookManager(container)
    task_manager = BackgroundTaskManager(container, max_workers=2)

    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)
    container.register("task_manager", lambda: task_manager, singleton=True)
    
    # 手动加载所有核心插件
    register_engine_plugin(container, hook_manager)
    register_llm_plugin(container, hook_manager)
    register_memoria_plugin(container, hook_manager)

    # 手动触发异步钩子来填充服务
    await container.resolve("hook_manager").trigger("services_post_register", container=container)

    engine = container.resolve("execution_engine")
    
    task_manager.start()
    yield engine, container, hook_manager
    await task_manager.stop()


@pytest.fixture
def memoria_sandbox_factory(
    memoria_test_setup: Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface]
) -> Callable[..., Sandbox]:
    """
    【全新的 Fixture】
    一个专门为 memoria 测试服务的沙盒工厂。
    它使用了只包含 memoria 及其依赖的隔离引擎环境。
    """
    _, container, _ = memoria_test_setup
    
    def _create_sandbox(
        graph_collection_dict: Dict[str, Any],
        initial_lore: Optional[Dict[str, Any]] = None,
        initial_moment: Optional[Dict[str, Any]] = None
    ) -> Sandbox:
        sandbox_id = uuid4()
        
        lore_data = initial_lore or {}
        moment_data = initial_moment or {}

        # 将图定义自动放入 Lore 中
        lore_data['graphs'] = graph_collection_dict

        definition = {
            "initial_lore": lore_data,
            "initial_moment": moment_data
        }

        sandbox = Sandbox(
            id=sandbox_id,
            name="Memoria Test Sandbox",
            definition=definition,
            lore=lore_data,
        )

        genesis_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            moment=moment_data
        )

        sandbox.head_snapshot_id = genesis_snapshot.id
        
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        snapshot_store.save(genesis_snapshot)
        
        sandbox_store: Dict[uuid4, Sandbox] = container.resolve("sandbox_store")
        sandbox_store[sandbox.id] = sandbox

        return sandbox

    return _create_sandbox