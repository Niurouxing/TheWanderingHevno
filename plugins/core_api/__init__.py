# plugins/core_api/__init__.py
import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager
from .contracts import Reportable

from .auditor import Auditor
from .base_router import router as base_router
from .sandbox_router import router as sandbox_router

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor() -> Auditor:
    return Auditor([])

# --- 钩子实现 ---
# 签名简化：可以直接索取 container 和 hook_manager
async def populate_auditor(container: Container, hook_manager: HookManager):
    logger.debug("Async task: Populating auditor with reporters...")
    auditor: Auditor = container.resolve("auditor")
    
    # filter 调用时不再需要手动传递 container
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")

# 签名简化：这个钩子不需要 container，所以就不声明它
async def provide_own_routers(routers: List[APIRouter]) -> List[APIRouter]:
    routers.append(base_router)
    routers.append(sandbox_router)
    logger.debug("Provided own routers (base, sandbox) to the application.")
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
        priority=100,
        plugin_name="core-api"
    )
    logger.info("插件 [core-api] 注册成功。")