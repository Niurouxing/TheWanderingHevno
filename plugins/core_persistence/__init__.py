# plugins/core_persistence/__init__.py
import os
import logging

from backend.core.contracts import Container, HookManager
from .service import PersistenceService

from .api import persistence_router

logger = logging.getLogger(__name__)

def _create_persistence_service() -> PersistenceService:
    assets_dir = os.getenv("HEVNO_ASSETS_DIR", "assets")
    return PersistenceService(assets_base_dir=assets_dir)

async def provide_router(routers: list) -> list:

    routers.append(persistence_router)
    logger.debug("Provided 'persistence_router' to the application.")
    return routers

def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_persistence] 插件...")
    
    container.register("persistence_service", _create_persistence_service)
    logger.debug("服务 'persistence_service' 已注册。")
    
    hook_manager.add_implementation("collect_api_routers", provide_router, plugin_name="core_persistence")
    logger.debug("钩子实现 'collect_api_routers' 已注册。")
    
    logger.info("插件 [core_persistence] 注册成功。")