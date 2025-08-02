# plugins/core_engine/__init__.py

import logging
from typing import Dict, Type

from backend.core.contracts import Container, HookManager
from .engine import ExecutionEngine
from .registry import RuntimeRegistry
from .state import SnapshotStore
from .interfaces import RuntimeInterface
from .runtimes.base_runtimes import InputRuntime, SetWorldVariableRuntime
from .runtimes.control_runtimes import ExecuteRuntime, CallRuntime, MapRuntime

logger = logging.getLogger(__name__)

# --- 服务工厂 ---

def _create_runtime_registry() -> RuntimeRegistry:
    """工厂：仅创建 RuntimeRegistry 的【空】实例，并注册内置运行时。"""
    registry = RuntimeRegistry()
    logger.debug("RuntimeRegistry instance created.")

    base_runtimes: Dict[str, Type[RuntimeInterface]] = {
        "system.input": InputRuntime,
        "system.set_world_var": SetWorldVariableRuntime,
        "system.execute": ExecuteRuntime,
        "system.call": CallRuntime,
        "system.map": MapRuntime,
    }
    for name, runtime_class in base_runtimes.items():
        registry.register(name, runtime_class)
    logger.info(f"Registered {len(base_runtimes)} built-in system runtimes.")
    return registry

def _create_execution_engine(container: Container) -> ExecutionEngine:
    """工厂：创建执行引擎，并注入其所有依赖。"""
    logger.debug("Creating ExecutionEngine instance...")
    return ExecutionEngine(
        registry=container.resolve("runtime_registry"),
        container=container,
        hook_manager=container.resolve("hook_manager")
    )

# --- 钩子实现 ---
async def populate_runtime_registry(container: Container):
    """
    【新】钩子实现：监听应用启动事件，【异步地】收集并填充运行时注册表。
    """
    logger.debug("Async task: Populating runtime registry from other plugins...")
    hook_manager = container.resolve("hook_manager")
    registry = container.resolve("runtime_registry")

    external_runtimes: Dict[str, Type[RuntimeInterface]] = await hook_manager.filter("collect_runtimes", {})
    
    if not external_runtimes:
        logger.info("No external runtimes discovered from other plugins.")
        return

    logger.info(f"Discovered {len(external_runtimes)} external runtime(s): {list(external_runtimes.keys())}")
    for name, runtime_class in external_runtimes.items():
        registry.register(name, runtime_class)

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-engine] 插件...")

    container.register("snapshot_store", lambda: SnapshotStore(), singleton=True)
    container.register("sandbox_store", lambda: {}, singleton=True)
    
    # 注册工厂，它只做同步部分
    container.register("runtime_registry", _create_runtime_registry, singleton=True)
    container.register("execution_engine", _create_execution_engine, singleton=True)
    
    # 【新】注册一个监听器，它将在应用启动的异步阶段被调用
    hook_manager.add_implementation(
        "services_post_register", 
        populate_runtime_registry, 
        plugin_name="core-engine"
    )

    logger.info("插件 [core-engine] 注册成功。")