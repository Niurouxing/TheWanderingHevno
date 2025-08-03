# plugins/core_llm/__init__.py

import logging
import os
from typing import List, Dict, Type

# 从平台核心导入接口和类型
from backend.core.contracts import Container, HookManager

# 导入本插件内部的组件
from .service import LLMService, MockLLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import ProviderRegistry
from .runtime import LLMRuntime
from .reporters import LLMProviderReporter
from .providers.base import LLMProvider
from .providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)

# --- 服务工厂 (Service Factories) ---

def _create_provider_registry() -> ProviderRegistry:
    """工厂：创建 ProviderRegistry 的【空】实例。"""
    return ProviderRegistry()

def _create_llm_service(container: Container) -> LLMService | MockLLMService:
    """这个工厂函数现在只负责创建服务，不再负责填充注册表。"""
    is_debug_mode = os.getenv("HEVNO_LLM_DEBUG_MODE", "false").lower() == "true"
    if is_debug_mode:
        logger.warning("LLM Gateway is in MOCK/DEBUG mode.")
        return MockLLMService()

    # 依赖容器来获取已注册（但可能尚未填充）的服务
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

    return LLMService(
        key_manager=key_manager,
        provider_registry=provider_registry,
        max_retries=3
    )

def _create_key_pool_manager() -> KeyPoolManager:
    """工厂：创建 KeyPoolManager。"""
    cred_manager = CredentialManager()
    return KeyPoolManager(credential_manager=cred_manager)


# --- 钩子实现 (Hook Implementations) ---

async def provide_llm_providers(providers: Dict[str, Dict[str, any]]) -> Dict[str, Dict[str, any]]:
    """钩子实现：向系统中提供本插件知道的所有 LLM Provider。"""
    if "gemini" not in providers:
        providers["gemini"] = {
            "class": GeminiProvider,
            "key_env_var": "GEMINI_API_KEYS"
        }
    # 如果有其他 providers，也在这里添加
    return providers

async def populate_llm_services(container: Container):
    """
    钩子实现：监听 'services_post_register'。
    异步地收集所有 provider，填充注册表，并配置密钥管理器。
    """
    logger.debug("Async task: Populating LLM services...")
    hook_manager = container.resolve("hook_manager")
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

    # 1. 触发钩子，收集所有 provider 的信息
    all_providers: Dict[str, Dict[str, any]] = await hook_manager.filter("collect_llm_providers", {})
    
    if not all_providers:
        logger.warning("No LLM providers were collected. LLM service will not be functional.")
        return

    # 2. 用收集到的信息填充注册表和密钥管理器
    for name, info in all_providers.items():
        provider_class = info.get("class")
        key_env_var = info.get("key_env_var")
        if provider_class and key_env_var:
            provider_registry.register(name, provider_class, key_env_var)
            key_manager.register_provider(name, key_env_var)

    # 3. 实例化所有 provider
    provider_registry.instantiate_all()
    logger.info(f"LLM Provider Registry populated with {len(all_providers)} provider(s).")


async def provide_runtime(runtimes: dict) -> dict:
    """钩子实现：向引擎注册 'llm.default' 运行时。"""
    if "llm.default" not in runtimes:
        runtimes["llm.default"] = LLMRuntime
        logger.debug("Provided 'llm.default' runtime to the engine.")
    return runtimes

async def provide_reporter(reporters: list, *, container: Container) -> list:
    """
    钩子实现：向审计员提供本插件的报告器。
    我们在这里从容器解析依赖，并实例化报告器。
    
    注意：container 被定义为关键字参数，以匹配 hook_manager.filter 的调用方式。
    """
    provider_registry = container.resolve("provider_registry")
    reporters.append(LLMProviderReporter(provider_registry))
    logger.debug("Provided 'LLMProviderReporter' to the auditor.")
    return reporters


# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    """这是 core-llm 插件的注册入口，由平台加载器调用。"""
    logger.info("--> 正在注册 [core-llm] 插件...")

    # 1. 注册服务（同步创建空实例或简单实例）
    container.register("provider_registry", _create_provider_registry)
    container.register("key_pool_manager", _create_key_pool_manager)
    container.register("llm_service", _create_llm_service)
    logger.debug("Services 'provider_registry', 'key_pool_manager', 'llm_service' registered.")

    # 2. 注册【异步填充】服务的钩子
    hook_manager.add_implementation(
        "services_post_register",
        populate_llm_services,
        plugin_name="core-llm"
    )

    # 3. 注册【提供能力】的钩子
    hook_manager.add_implementation(
        "collect_llm_providers",
        provide_llm_providers,
        plugin_name="core-llm"
    )
    hook_manager.add_implementation(
        "collect_runtimes", 
        provide_runtime, 
        plugin_name="core-llm"
    )
    # 修改 'collect_reporters' 的钩子，因为现在它需要容器
    # 我们用 lambda 来适配钩子签名
    hook_manager.add_implementation(
        "collect_reporters",
        provide_reporter, 
        plugin_name="core-llm"
    )
    logger.debug("Hook implementations registered.")
    
    logger.info("插件 [core-llm] 注册成功。")