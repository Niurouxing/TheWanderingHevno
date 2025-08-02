# plugins/core_persistence/__init__.py
import os
import logging

from backend.core.contracts import Container, HookManager
from .service import PersistenceService
from .api import router as persistence_router

logger = logging.getLogger(__name__)

def _create_persistence_service() -> PersistenceService:
    """服务工厂：创建 PersistenceService 实例。"""
    assets_dir = os.getenv("HEVNO_ASSETS_DIR", "assets")
    return PersistenceService(assets_base_dir=assets_dir)

async def provide_router(routers: list) -> list:
    """钩子实现：提供本插件的 API 路由。"""
    routers.append(persistence_router)
    return routers

def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core_persistence 插件的注册入口。"""
    # 统一的入口消息
    logger.info("--> 正在注册 [core-persistence] 插件...")
    
    # 注册服务
    container.register("persistence_service", _create_persistence_service)
    logger.debug("服务 'persistence_service' 已注册。")
    
    # 注册钩子
    hook_manager.add_implementation("collect_api_routers", provide_router, plugin_name="core_persistence")
    logger.debug("钩子实现 'collect_api_routers' 已注册。")
    
    # 统一的成功消息
    logger.info("插件 [core-persistence] 注册成功。")