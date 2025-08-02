# plugins/core_api/__init__.py

import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager, Reportable
from .auditor import Auditor
from .base_router import router as base_router
from .sandbox_router import router as sandbox_router

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor() -> Auditor:
    """工厂：只创建 Auditor 的空实例。它的内容将在之后被异步填充。"""
    return Auditor([])

# --- 钩子实现 ---
async def populate_auditor(container: Container):
    """钩子实现：监听启动事件，异步地收集报告器并填充 Auditor。"""
    logger.debug("Async task: Populating auditor with reporters...")
    hook_manager = container.resolve("hook_manager")
    auditor: Auditor = container.resolve("auditor")
    
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")

async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的路由添加到收集中。"""
    routers.append(base_router)
    routers.append(sandbox_router)
    logger.debug("Provided own routers (base, sandbox) to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-api] 插件...")

    # 1. 注册服务（仅创建空实例）
    container.register("auditor", _create_auditor, singleton=True)
    logger.debug("服务 'auditor' 已注册 (initially empty)。")

    # 2. 注册异步填充钩子
    hook_manager.add_implementation(
        "services_post_register",
        populate_auditor,
        plugin_name="core-api"
    )

    # 3. 【关键】注册路由【提供者】钩子
    #    它现在和其他插件一样，只是一个提供者。
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100, # 较高的 priority 意味着后执行
        plugin_name="core-api"
    )
    logger.debug("钩子实现 'collect_api_routers' 和 'services_post_register' 已注册。")

    logger.info("插件 [core-api] 注册成功。")