# plugins/core_diagnostics/__init__.py
import logging
from typing import List
from fastapi import APIRouter

from backend.core.contracts import Container, HookManager
from .contracts import Reportable, AuditorInterface
from .auditor import Auditor
from .reporters import PluginReporter
from .api import diagnostics_router  # 导入新创建的路由器

logger = logging.getLogger(__name__)

# --- 服务工厂 (保持不变) ---
def _create_auditor() -> Auditor:
    return Auditor([])

# --- 钩子实现 ---

async def populate_auditor(container: Container, hook_manager: HookManager):
    """钩子实现：异步地从其他插件收集报告器，并填充到审计员中。"""
    logger.debug("Async task: Populating auditor with reporters...")
    auditor: AuditorInterface = container.resolve("auditor")
    # 注意：这里的初始值必须是空列表 []
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")


async def provide_plugin_reporter(reporters: List[Reportable], container: Container) -> List[Reportable]:
    """钩子实现：向审计员提供本插件的插件报告器。"""
    loaded_manifests = container.resolve("loaded_plugins_manifests")
    reporters.append(PluginReporter(loaded_manifests=loaded_manifests))
    logger.debug("Provided 'PluginReporter' to the auditor.")
    return reporters

# --- 【关键新增】提供API路由的钩子实现 ---
async def provide_api_routers(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的 diagnostics_router 添加到应用中。"""
    routers.append(diagnostics_router)
    logger.debug("Provided diagnostics API router to the application.")
    return routers

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_diagnostics] 插件...")

    # 1. 注册服务
    container.register("auditor", _create_auditor, singleton=True)
    
    # 2. 注册钩子实现
    hook_manager.add_implementation(
        "services_post_register",
        populate_auditor,
        plugin_name="core_diagnostics"
    )

    hook_manager.add_implementation(
        "collect_reporters",
        provide_plugin_reporter,
        plugin_name="core_diagnostics"
    )
    
    # 3. 【关键新增】注册提供API路由的钩子
    hook_manager.add_implementation(
        "collect_api_routers",
        provide_api_routers,
        plugin_name="core_diagnostics"
    )
    
    logger.info("插件 [core_diagnostics] 注册成功。")