# plugins/core_llm/__init__.py

import logging
import os
import json
from typing import List, Dict, Any, Type
from fastapi import APIRouter, Depends

from backend.core.contracts import Container, HookManager

from .service import LLMService
from .manager import KeyPoolManager, CredentialManager
from .registry import ProviderRegistry
from .runtime import LLMRuntime
from .reporters import LLMProviderReporter
from .providers.base import LLMProvider
from .providers.gemini import GeminiProvider
from .providers.mock import MockProvider
from .providers.openai_compatible import OpenAICompatibleProvider
from .config_api import config_api_router
from .factory import ProviderFactory
from .utils import parse_provider_configs_from_env

logger = logging.getLogger(__name__)

def _create_provider_registry() -> ProviderRegistry:
    """创建 ProviderRegistry 实例。"""
    return ProviderRegistry()


def _create_llm_service(container: Container) -> LLMService:
    """创建 LLMService 实例。"""
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

    return LLMService(
        key_manager=key_manager,
        provider_registry=provider_registry,
        max_retries=3
    )


def _create_key_pool_manager() -> KeyPoolManager:
    """创建 KeyPoolManager。"""
    cred_manager = CredentialManager()
    return KeyPoolManager(credential_manager=cred_manager)


async def populate_llm_services(container: Container, hook_manager: HookManager):
    """在服务注册后动态注册内置与自定义的 LLM 提供商。"""
    logger.debug("Async task: Populating LLM services...")
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

    gemini_provider = GeminiProvider()
    provider_registry.register("gemini", gemini_provider, "GEMINI_API_KEYS")
    key_manager.register_provider("gemini", "GEMINI_API_KEYS")

    mock_provider = MockProvider()
    mock_env_var = "MOCK_API_KEYS_DUMMY"
    provider_registry.register("mock", mock_provider, mock_env_var)
    key_manager.register_provider("mock", mock_env_var)

    custom_configs = parse_provider_configs_from_env()
    for provider_id, config in custom_configs.items():
        if not all([config["type"], config["base_url"], config["keys_env_var"]]):
            logger.warning(f"Skipping custom provider '{provider_id}' due to missing configuration.")
            continue

        factory = ProviderFactory(initial_config=config)
        container.register(f"provider_factory_{provider_id}", lambda: factory, singleton=True)

        container.register(
            provider_id,
            lambda c, pid=provider_id: c.resolve(f"provider_factory_{pid}").get_provider(),
            singleton=False
        )

        try:
            provider_instance = container.resolve(provider_id)
            provider_registry.register(provider_id, provider_instance, config["keys_env_var"])
            key_manager.register_provider(provider_id, config["keys_env_var"])
            logger.info(f"Dynamically registered custom provider '{provider_id}'.")
        except Exception as e:
            logger.error(f"Failed to register custom provider '{provider_id}': {e}", exc_info=True)

    provider_registry.build_capability_map()

    logger.info(f"LLM Provider Registry populated. Providers: {provider_registry.get_all_provider_names()}")


async def provide_runtime(runtimes: dict) -> dict:
    """向引擎提供默认 LLM 运行时。"""
    if "llm.default" not in runtimes:
        runtimes["llm.default"] = LLMRuntime
        logger.debug("Provided 'llm.default' runtime to the engine.")
    return runtimes


async def provide_reporter(reporters: list, container: Container) -> list:
    """向审计系统提供本插件的报告器。"""
    provider_registry = container.resolve("provider_registry")
    reporters.append(LLMProviderReporter(provider_registry))
    logger.debug("Provided 'LLMProviderReporter' to the auditor.")
    return reporters


async def provide_api_router(routers: List[APIRouter]) -> List[APIRouter]:
    """向应用添加本插件的 API 路由。"""
    routers.append(config_api_router)
    logger.debug("Provided LLM configuration API router to the application.")
    return routers


def register_plugin(container: Container, hook_manager: HookManager):
    logger.info("--> 正在注册 [core_llm] 插件...")

    container.register("provider_registry", _create_provider_registry, singleton=True)
    container.register("key_pool_manager", _create_key_pool_manager, singleton=True)
    container.register("llm_service", _create_llm_service, singleton=True)

    hook_manager.add_implementation("services_post_register", populate_llm_services, plugin_name="core_llm")
    hook_manager.add_implementation("collect_runtimes", provide_runtime, plugin_name="core_llm")
    hook_manager.add_implementation("collect_api_routers", provide_api_router, plugin_name="core_llm")
    hook_manager.add_implementation("collect_reporters", provide_reporter, plugin_name="core_llm")

    logger.info("插件 [core_llm] 注册成功。")