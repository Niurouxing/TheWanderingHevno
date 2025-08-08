# plugins/core_api/__init__.py
import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager


from .base_router import router as base_router
from .system_router import api_plugins_router, frontend_assets_router

logger = logging.getLogger(__name__)


async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的所有路由添加到收集中。"""
    routers.append(base_router)
    routers.append(api_plugins_router)
    routers.append(frontend_assets_router)
    logger.debug("Provided own routers (base, system, assets) to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_api] 插件...")
    
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100,
        plugin_name="core_api"
    )
    logger.info("插件 [core_api] 注册成功。")