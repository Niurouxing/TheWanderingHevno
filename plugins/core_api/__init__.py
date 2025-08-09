# plugins/core_api/__init__.py
import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager

# 【修复】移除所有顶层的路由导入，避免过早执行路由模块的代码
# from .base_router import router as base_router
# from .system_router import api_plugins_router, frontend_assets_router

logger = logging.getLogger(__name__)


async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的所有路由添加到收集中。"""
    
    # 将导入语句移至函数内部。
    # 这确保了 base_router.py 和 system_router.py 只有在钩子被调用时才会被执行，
    # 此时整个应用已经准备就绪。
    logger.info("--> [core_api] 'collect_api_routers' hook triggered. Importing routers now...")
    from .base_router import router as base_router
    from .system_router import api_plugins_router, frontend_assets_router
    
    # 记录将要添加的路由对象
    logger.debug(f"[core_api] Appending base_router (prefix='{base_router.prefix}', {len(base_router.routes)} routes)")
    logger.debug(f"[core_api] Appending api_plugins_router (prefix='{api_plugins_router.prefix}', {len(api_plugins_router.routes)} routes)")
    logger.debug(f"[core_api] Appending frontend_assets_router (prefix='{frontend_assets_router.prefix}', {len(frontend_assets_router.routes)} routes)")
    
    routers.append(base_router)
    routers.append(api_plugins_router)
    routers.append(frontend_assets_router)
    
    logger.info("--> [core_api] Routers have been appended to the collection.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_api] 插件...")
    
    hook_manager.add_implementation(
        "collect_api_routers", 
        provide_own_routers, 
        priority=100,  # 保持高优先级
        plugin_name="core_api"
    )
    logger.info("插件 [core_api] 注册成功，'collect_api_routers' hook已实现。")