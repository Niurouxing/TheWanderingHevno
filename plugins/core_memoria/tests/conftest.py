# plugins/core_memoria/tests/conftest.py (新文件)

import pytest_asyncio
from typing import AsyncGenerator, Tuple

# 从平台核心导入组件
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.tasks import BackgroundTaskManager

# 从平台核心导入接口
from backend.core.contracts import (
    Container as ContainerInterface,
    HookManager as HookManagerInterface
)

# 从依赖插件导入注册函数和组件
from plugins.core_engine.engine import ExecutionEngine as ExecutionEngineInterface
from plugins.core_engine import register_plugin as register_engine_plugin
from plugins.core_engine.engine import ExecutionEngine # 导入具体实现以进行实例化
from plugins.core_llm import register_plugin as register_llm_plugin

# 从当前插件导入注册函数
from .. import register_plugin as register_memoria_plugin


@pytest_asyncio.fixture
async def memoria_test_engine() -> AsyncGenerator[Tuple[ExecutionEngineInterface, ContainerInterface, HookManagerInterface], None]:
    """
    一个专门为 core-memoria 插件测试定制的 fixture。
    
    它只加载运行 memoria 功能所必需的插件 (core-engine, core-llm, core-memoria)，
    从而提供一个轻量级、隔离的测试环境。
    """
    # 1. 初始化平台核心服务
    container = Container()
    hook_manager = HookManager(container)
    
    # 手动创建并注册后台任务管理器
    task_manager = BackgroundTaskManager(container, max_workers=2)
    container.register("task_manager", lambda: task_manager, singleton=True)
    container.register("hook_manager", lambda: hook_manager, singleton=True)
    container.register("container", lambda: container, singleton=True)

    # 2. 手动按依赖顺序注册所需插件
    #    这模拟了 PluginLoader 的行为，但范围更小。
    register_engine_plugin(container, hook_manager)
    register_llm_plugin(container, hook_manager)
    register_memoria_plugin(container, hook_manager) # 注册我们自己

    # 3. 手动触发服务初始化钩子
    #    这对于 core-engine 填充其运行时注册表至关重要。
    await hook_manager.trigger('services_post_register', container=container)

    # 4. 从容器中解析出最终配置好的引擎实例
    engine = container.resolve("execution_engine")
    
    # 启动后台任务管理器
    task_manager.start()

    # 5. Yield 元组，供测试使用
    yield engine, container, hook_manager
    
    # 6. 测试结束后，优雅地清理
    await task_manager.stop()