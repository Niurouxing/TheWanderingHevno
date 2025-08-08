# plugins/core_diagnostics/__init__.py
import logging
from typing import List

from backend.core.contracts import Container, HookManager
from .contracts import Reportable
from .auditor import Auditor

logger = logging.getLogger(__name__)

# --- 服务工厂 ---
def _create_auditor() -> Auditor:
    return Auditor([])

# --- 钩子实现 ---
async def populate_auditor(container: Container, hook_manager: HookManager):
    """钩子实现：异步地从其他插件收集报告器，并填充到审计员中。"""
    logger.debug("Async task: Populating auditor with reporters...")
    auditor: Auditor = container.resolve("auditor")
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_diagnostics] 插件...")

    # 1. 注册 Auditor 服务
    container.register("auditor", _create_auditor, singleton=True)
    
    # 2. 注册一个钩子，它会在启动后期填充 Auditor
    hook_manager.add_implementation(
        "services_post_register",
        populate_auditor,
        plugin_name="core_diagnostics"
    )
    
    logger.info("插件 [core_diagnostics] 注册成功。")