# plugins/core_engine/__init__.py

import logging
from typing import Dict, Type, List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager
from .engine import ExecutionEngine
from .registry import RuntimeRegistry
from .state import SnapshotStore
from .contracts import RuntimeInterface
from .evaluation_service import MacroEvaluationService

# --- 从新的运行时模块和API模块导入 ---
from .runtimes.io_runtimes import InputRuntime, LogRuntime
from .runtimes.data_runtimes import FormatRuntime, ParseRuntime, RegexRuntime
from .runtimes.flow_runtimes import ExecuteRuntime, CallRuntime, MapRuntime
from .api import router as sandbox_router


logger = logging.getLogger(__name__)

# --- 服务工厂  ---
def _create_runtime_registry() -> RuntimeRegistry:
    registry = RuntimeRegistry()
    base_runtimes: Dict[str, Type[RuntimeInterface]] = {
        "system.io.input": InputRuntime, "system.io.log": LogRuntime,
        "system.data.format": FormatRuntime, "system.data.parse": ParseRuntime, "system.data.regex": RegexRuntime,
        "system.flow.call": CallRuntime, "system.flow.map": MapRuntime, "system.execute": ExecuteRuntime,
    }
    for name, runtime_class in base_runtimes.items():
        registry.register(name, runtime_class)
    logger.info(f"Registered {len(base_runtimes)} built-in system runtimes.")
    return registry

def _create_execution_engine(container: Container) -> ExecutionEngine:
    return ExecutionEngine(
        registry=container.resolve("runtime_registry"),
        container=container,
        hook_manager=container.resolve("hook_manager")
    )

# --- 钩子实现 ---
async def populate_runtime_registry(container: Container):
    logger.debug("Async task: Populating runtime registry from other plugins...")
    hook_manager = container.resolve("hook_manager")
    registry = container.resolve("runtime_registry")
    external_runtimes: Dict[str, Type[RuntimeInterface]] = await hook_manager.filter("collect_runtimes", {})
    if external_runtimes:
        logger.info(f"Discovered {len(external_runtimes)} external runtime(s): {list(external_runtimes.keys())}")
        for name, runtime_class in external_runtimes.items():
            registry.register(name, runtime_class)

# --- (新) 钩子实现：提供API路由 ---
async def provide_api_router(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的路由添加到收集中。"""
    routers.append(sandbox_router)
    logger.debug("Provided sandbox API router to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_engine] 插件...")

    container.register("snapshot_store", lambda: SnapshotStore(), singleton=True)
    container.register("sandbox_store", lambda: {}, singleton=True)
    container.register("runtime_registry", _create_runtime_registry, singleton=True)
    container.register("execution_engine", _create_execution_engine, singleton=True)
    container.register("macro_evaluation_service", lambda: MacroEvaluationService(), singleton=True)
    
    hook_manager.add_implementation(
        "services_post_register", 
        populate_runtime_registry, 
        plugin_name="core_engine"
    )
    
    # --- 注册提供API路由的钩子 ---
    hook_manager.add_implementation(
        "collect_api_routers",
        provide_api_router,
        plugin_name="core_engine"
    )

    logger.info("插件 [core_engine] 注册成功。")