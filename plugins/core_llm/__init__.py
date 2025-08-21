# plugins/core_llm/__init__.py

import logging
import os
import json
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
# 导入我们新创建的 provider
from .providers.openai_compatible import OpenAICompatibleProvider
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

async def populate_llm_services(container: Container, hook_manager: HookManager):
    """
    钩子实现：监听 'services_post_register'。
    现在它负责实例化所有 providers 并填充注册表。
    """
    logger.debug("Async task: Populating LLM services...")
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

    # 1. 注册内置的 Gemini 提供商
    gemini_provider = GeminiProvider()
    gemini_env_var = "GEMINI_API_KEYS"
    provider_registry.register("gemini", gemini_provider, gemini_env_var)
    key_manager.register_provider("gemini", gemini_env_var)

    # 2. 注册内置的 Mock 提供商
    mock_provider = MockProvider()
    mock_env_var = "MOCK_API_KEYS_DUMMY"
    provider_registry.register("mock", mock_provider, mock_env_var)
    # Mock provider 不需要密钥池，但注册一下无妨
    key_manager.register_provider("mock", mock_env_var)

    # 3. 【新】动态注册自定义 OpenAI 兼容提供商
    custom_provider_name = "openai_custom"
    custom_base_url = os.getenv("OPENAI_CUSTOM_BASE_URL")
    custom_env_var = "OPENAI_CUSTOM_API_KEYS"

    if custom_base_url:
        logger.info(f"检测到自定义提供商配置，URL: {custom_base_url}")
        
        # 解析模型映射
        mapping_str = os.getenv("OPENAI_CUSTOM_MODEL_MAPPING", "")
        model_mapping = {}
        if mapping_str:
            try:
                # 优先尝试解析为JSON
                model_mapping = json.loads(mapping_str)
                if not isinstance(model_mapping, dict):
                    raise ValueError("JSON must be an object.")
            except (json.JSONDecodeError, ValueError):
                # 如果JSON解析失败，回退到 key:value,key:value 格式
                model_mapping = dict(
                    item.split(":", 1) for item in mapping_str.split(",") if ":" in item
                )
            logger.info(f"加载自定义模型映射: {model_mapping}")

        custom_provider = OpenAICompatibleProvider(
            base_url=custom_base_url,
            model_mapping=model_mapping
        )
        provider_registry.register(custom_provider_name, custom_provider, custom_env_var)
        key_manager.register_provider(custom_provider_name, custom_env_var)
    
    logger.info(f"LLM Provider Registry populated. Providers: {provider_registry.get_all_provider_names()}")


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

    container.register("provider_registry", _create_provider_registry, singleton=True)
    container.register("key_pool_manager", _create_key_pool_manager, singleton=True)
    container.register("llm_service", _create_llm_service, singleton=True)

    hook_manager.add_implementation("services_post_register", populate_llm_services, plugin_name="core_llm")
    # 不再需要 collect_llm_providers
    hook_manager.add_implementation("collect_runtimes", provide_runtime, plugin_name="core_llm")
    hook_manager.add_implementation("collect_api_routers", provide_api_router, plugin_name="core_llm")
    hook_manager.add_implementation("collect_reporters", provide_reporter, plugin_name="core_llm")

    logger.info("插件 [core_llm] 注册成功。")