# plugins/core_api/__init__.py
import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager
from .contracts import Reportable

from .auditor import Auditor
from .base_router import router as base_router
from .sandbox_router import router as sandbox_router
# 【修改】从 system_router.py 导入两个路由器
from .system_router import api_plugins_router, frontend_assets_router

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor() -> Auditor:
    return Auditor([])

# --- 钩子实现 ---
async def populate_auditor(container: Container, hook_manager: HookManager):
    logger.debug("Async task: Populating auditor with reporters...")
    auditor: Auditor = container.resolve("auditor")
    
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")

async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的所有路由添加到收集中。"""
    routers.append(base_router)
    routers.append(sandbox_router)
    # 【修改】添加两个系统相关的路由器
    routers.append(api_plugins_router)
    routers.append(frontend_assets_router)
    logger.debug("Provided own routers (base, sandbox, system, assets) to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core-api] 插件...")

    container.register("auditor", _create_auditor, singleton=True)
    
    hook_manager.add_implementation(
        "services_post_register",
        populate_auditor,
        plugin_name="core-api"
    )
    
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100, # 保持高优先级，确保这些核心路由被正确注册
        plugin_name="core-api"
    )
    logger.info("插件 [core-api] 注册成功。")