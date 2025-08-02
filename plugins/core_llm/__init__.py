# plugins/core_llm/__init__.py 

import logging
import os

# 从平台核心导入接口和类型
from backend.core.contracts import Container, HookManager

# 导入本插件内部的组件
from .service import LLMService, MockLLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import provider_registry
from .runtime import LLMRuntime
from .reporters import LLMProviderReporter

# 动态加载所有 provider
from backend.core.loader import load_modules
load_modules(["plugins.core_llm.providers"])

logger = logging.getLogger(__name__)

# --- 服务工厂 (Service Factories) ---
def _create_llm_service(container: Container) -> LLMService:
    """这个工厂函数封装了创建 LLMService 的复杂逻辑。"""
    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    if is_debug_mode:
        logger.warning("LLM Gateway is in MOCK/DEBUG mode.")
        return MockLLMService()

    provider_registry.instantiate_all()
    cred_manager = CredentialManager()
    key_manager = KeyPoolManager(credential_manager=cred_manager)
    
    for name, info in provider_registry.get_all_provider_info().items():
        key_manager.register_provider(name, info.key_env_var)

    return LLMService(
        key_manager=key_manager,
        provider_registry=provider_registry,
        max_retries=3
    )

# --- 钩子实现 (Hook Implementations) ---
async def provide_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册本插件提供的 'llm.default' 运行时。"""
    if "llm.default" not in runtimes:
        runtimes["llm.default"] = LLMRuntime
        logger.debug("Provided 'llm.default' runtime to the engine.")
    return runtimes

async def provide_reporter(reporters: list) -> list:
    """钩子实现：向审计员提供本插件的报告器。"""
    reporters.append(LLMProviderReporter())
    logger.debug("Provided 'LLMProviderReporter' to the auditor.")
    return reporters

# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-llm 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-llm] 插件...")

    # 1. 注册服务到 DI 容器
    #    'llm_service' 是单例，它的创建逻辑被封装在工厂函数中。
    container.register("llm_service", _create_llm_service)
    logger.debug("服务 'llm_service' 已注册。")

    # 2. 注册钩子实现
    #    通过 'collect_runtimes' 钩子，将我们的运行时提供给 core_engine。
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_runtime, 
        plugin_name="core-llm"
    )
    #    通过 'collect_reporters' 钩子，将我们的报告器提供给 core_api。
    hook_manager.add_implementation(
        "collect_reporters",
        provide_reporter,
        plugin_name="core-llm"
    )
    logger.debug("钩子实现 'collect_runtimes' 和 'collect_reporters' 已注册。")
    
    logger.info("插件 [core-llm] 注册成功。")