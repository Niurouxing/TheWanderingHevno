# plugins/core_persistence/__init__.py
import os
import logging

from backend.core.contracts import Container, HookManager
from .service import PersistenceService
from .stores import PersistentSandboxStore, PersistentSnapshotStore
from .api import persistence_router

logger = logging.getLogger(__name__)

def _create_persistent_sandbox_store(container: Container) -> PersistentSandboxStore:
    return PersistentSandboxStore(container.resolve("persistence_service"))

def _create_persistent_snapshot_store(container: Container) -> PersistentSnapshotStore:
    return PersistentSnapshotStore(container.resolve("persistence_service"))

def _create_persistence_service() -> PersistenceService:
    assets_dir = os.getenv("HEVNO_ASSETS_DIR", "assets")
    return PersistenceService(assets_base_dir=assets_dir)

async def provide_router(routers: list) -> list:
    routers.append(persistence_router)
    logger.debug("Provided 'persistence_router' to the application.")
    return routers

async def initialize_stores(container: Container):
    """钩子实现: 在所有服务注册后，异步初始化持久化存储。"""
    logger.info("Initializing persistent stores...")
    sandbox_store: PersistentSandboxStore = container.resolve("sandbox_store")
    
    sandbox_store.set_container(container)
    
    await sandbox_store.initialize()

def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_persistence] 插件...")
    container.register(
        "persistence_service", _create_persistence_service, singleton=True
    )
    container.register(
        "sandbox_store", _create_persistent_sandbox_store, singleton=True
    )
    container.register(
        "snapshot_store", _create_persistent_snapshot_store, singleton=True
    )
    logger.debug(
        "Registered 'sandbox_store' and 'snapshot_store' with persistent implementations."
    )
    hook_manager.add_implementation(
        "collect_api_routers", provide_router, plugin_name="core_persistence"
    )
    hook_manager.add_implementation(
        "services_post_register",
        initialize_stores,
        priority=90, 
        plugin_name="core_persistence",
    )
    logger.info("插件 [core_persistence] 注册成功。")