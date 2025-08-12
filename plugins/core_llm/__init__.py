# plugins/core_llm/__init__.py

import logging
import os
from typing import List, Dict, Type
from fastapi import APIRouter, Depends

# 从平台核心导入接口和类型
from backend.core.contracts import Container, HookManager

# 导入本插件内部的组件
from .service import LLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import ProviderRegistry
from .runtime import LLMRuntime
from .reporters import LLMProviderReporter
from .providers.base import LLMProvider
from .providers.gemini import GeminiProvider
from .providers.mock import MockProvider
from .config_api import config_api_router

logger = logging.getLogger(__name__)

# --- 服务工厂 (Service Factories) ---

def _create_provider_registry() -> ProviderRegistry:
    """工厂：创建 ProviderRegistry 的【空】实例。"""
    return ProviderRegistry()

def _create_llm_service(container: Container) -> LLMService:
    """这个工厂函数现在只负责创建服务，不再负责填充注册表。"""
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
    
    # 无条件注册模拟提供商
    if "mock" not in providers:
        providers["mock"] = {
            "class": MockProvider,
            "key_env_var": "MOCK_API_KEYS_DUMMY" # 虚拟变量，不会被找到，因此不会创建密钥池
        }
    
    return providers

async def populate_llm_services(container: Container, hook_manager: HookManager):
    """
    钩子实现：监听 'services_post_register'。
    异步地收集所有 provider，填充注册表，并配置密钥管理器。
    """
    logger.debug("Async task: Populating LLM services...")
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

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

async def provide_reporter(reporters: list, container: Container) -> list:
    """
    钩子实现：向审计员提供本插件的报告器。
    我们在这里从容器解析依赖，并实例化报告器。
    
    注意：container 被定义为关键字参数，以匹配 hook_manager.filter 的调用方式。
    """
    provider_registry = container.resolve("provider_registry")
    reporters.append(LLMProviderReporter(provider_registry))
    logger.debug("Provided 'LLMProviderReporter' to the auditor.")
    return reporters

async def provide_api_router(routers: List[APIRouter]) -> List[APIRouter]:
    """钩子实现：将本插件的配置API路由添加到收集中。"""
    routers.append(config_api_router)
    logger.debug("Provided LLM configuration API router to the application.")
    return routers



# --- 主注册函数 (Main Registration Function) ---
def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_llm] 插件...")

    container.register("provider_registry", _create_provider_registry)
    container.register("key_pool_manager", _create_key_pool_manager)
    container.register("llm_service", _create_llm_service)
    logger.debug("Services 'provider_registry', 'key_pool_manager', 'llm_service' registered.")

    hook_manager.add_implementation("services_post_register", populate_llm_services, plugin_name="core_llm")
    hook_manager.add_implementation("collect_llm_providers", provide_llm_providers, plugin_name="core_llm")
    hook_manager.add_implementation("collect_runtimes", provide_runtime, plugin_name="core_llm")
    hook_manager.add_implementation(
        "collect_api_routers",
        provide_api_router,
        plugin_name="core_llm"
    )
    
    # 移除 lambda，因为 HookManager 现在足够智能
    hook_manager.add_implementation("collect_reporters", provide_reporter, plugin_name="core_llm")

    logger.debug("Hook implementations registered.")
    logger.info("插件 [core_llm] 注册成功。")