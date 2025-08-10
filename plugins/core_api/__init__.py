# plugins/core_api/__init__.py
import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager


logger = logging.getLogger(__name__)


async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """
    Hook implementation: Adds this plugin's routers to the application's collection.
    By importing inside the function, we ensure the router modules are executed
    only when the application is ready to collect them.
    """
    logger.info("--> [core_api] 'collect_api_routers' hook triggered. Importing routers...")
    
    # 【重点】只从一个文件中导入，不再需要 base_router
    from .system_router import system_api_router, frontend_assets_router
    
    logger.debug(f"[core_api] Appending system_api_router (prefix='{system_api_router.prefix}', {len(system_api_router.routes)} routes)")
    logger.debug(f"[core_api] Appending frontend_assets_router (prefix='{frontend_assets_router.prefix}', {len(frontend_assets_router.routes)} routes)")
    
    routers.append(system_api_router)
    routers.append(frontend_assets_router)
    
    logger.info("--> [core_api] Routers have been provided.")
    return routers

# --- Main Registration Function ---
def register_plugin(container: Container, hook_manager: HookManager):
    """
    Registers the core_api plugin. Its sole backend purpose is to provide
    platform-level API endpoints for introspection and asset serving.
    """
    logger.info("--> 正在注册 [core_api] 插件...")
    
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100,  # High priority to ensure system routes are available
        plugin_name="core_api"
    )
    logger.info("插件 [core_api] 注册成功。'collect_api_routers' hook has been implemented.")