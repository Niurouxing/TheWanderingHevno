# plugins/core_diagnostics/__init__.py
import logging
from typing import List

from backend.core.contracts import Container, HookManager
from .contracts import Reportable
from .auditor import Auditor
from .reporters import PluginReporter 

logger = logging.getLogger(__name__)

# ... _create_auditor 和 populate_auditor 保持不变 ...
def _create_auditor() -> Auditor:
    return Auditor([])

async def populate_auditor(container: Container, hook_manager: HookManager):
    """钩子实现：异步地从其他插件收集报告器，并填充到审计员中。"""
    logger.debug("Async task: Populating auditor with reporters...")
    auditor: Auditor = container.resolve("auditor")
    reporters_list: List[Reportable] = await hook_manager.filter("collect_reporters", [])
    auditor.set_reporters(reporters_list)
    logger.info(f"Auditor populated with {len(reporters_list)} reporter(s).")


async def provide_plugin_reporter(reporters: List[Reportable], container: Container) -> List[Reportable]:
    """钩子实现：向审计员提供本插件的插件报告器。"""
    # 【修改】: 从容器中解析出已加载的插件清单
    loaded_manifests = container.resolve("loaded_plugins_manifests")
    reporters.append(PluginReporter(loaded_manifests=loaded_manifests))
    logger.debug("Provided 'PluginReporter' to the auditor.")
    return reporters

def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_diagnostics] 插件...")

    container.register("auditor", _create_auditor, singleton=True)
    
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
    
    logger.info("插件 [core_diagnostics] 注册成功。")