# plugins/core_codex/__init__.py
import logging
from fastapi import APIRouter
from typing import List
from backend.core.contracts import Container, HookManager

from .invoke_runtime import InvokeRuntime
# --- 导入新路由 ---
from .api import codex_router

logger = logging.getLogger(__name__)

# --- 钩子实现 ---
async def register_codex_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'codex.invoke' 运行时。"""
    runtimes["codex.invoke"] = InvokeRuntime 
    logger.debug("Runtime 'codex.invoke' provided to runtime registry.")
    return runtimes

# --- 钩子实现：提供API路由 ---
async def provide_api_router(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的 Codex 编辑器路由添加到收集中。"""
    routers.append(codex_router)
    logger.debug("Provided codex editor API router to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_codex] 插件...")

    # 注册运行时
    hook_manager.add_implementation(
        "collect_runtimes", 
        register_codex_runtime, 
        plugin_name="core_codex"
    )
    logger.debug("钩子实现 'collect_runtimes' 已注册。")

    # --- 注册API路由 ---
    hook_manager.add_implementation(
        "collect_api_routers",
        provide_api_router,
        plugin_name="core_codex"
    )
    logger.debug("钩子实现 'collect_api_routers' 已注册。")

    logger.info("插件 [core_codex] 注册成功。")