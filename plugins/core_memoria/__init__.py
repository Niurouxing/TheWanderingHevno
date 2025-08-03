# plugins/core_memoria/__init__.py

import logging
from backend.core.contracts import Container, HookManager

from .runtimes import MemoriaAddRuntime, MemoriaQueryRuntime, MemoriaAggregateRuntime

logger = logging.getLogger(__name__)

# --- 钩子实现 (Hook Implementation) ---
async def provide_memoria_runtimes(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的所有运行时。"""
    
    memoria_runtimes = {
        "memoria.add": MemoriaAddRuntime,
        "memoria.query": MemoriaQueryRuntime,
        "memoria.aggregate": MemoriaAggregateRuntime,
    }
    
    for name, runtime_class in memoria_runtimes.items():
        if name not in runtimes:
            runtimes[name] = runtime_class
            logger.debug(f"Provided '{name}' runtime to the engine.")
            
    return runtimes

# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-memoria 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-memoria] 插件...")

    # 本插件只提供运行时，它通过钩子与 core-engine 通信。
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_memoria_runtimes, 
        plugin_name="core-memoria"
    )
    logger.debug("钩子实现 'collect_runtimes' 已注册。")

    logger.info("插件 [core-memoria] 注册成功。")