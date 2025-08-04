# plugins/core_codex/__init__.py
import logging
from backend.core.contracts import Container, HookManager

from .invoke_runtime import InvokeRuntime

logger = logging.getLogger(__name__)

# --- 钩子实现 ---
async def register_codex_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'codex.invoke' 运行时。"""
    runtimes["codex.invoke"] = InvokeRuntime 
    logger.debug("Runtime 'codex.invoke' provided to runtime registry.")
    return runtimes

# --- 主注册函数 ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_codex] 插件...")

    # 本插件只提供运行时，不注册服务。
    # 它通过钩子与 core_engine 通信。
    hook_manager.add_implementation(
        "collect_runtimes", 
        register_codex_runtime, 
        plugin_name="core_codex"
    )
    logger.debug("钩子实现 'collect_runtimes' 已注册。")

    logger.info("插件 [core_codex] 注册成功。")