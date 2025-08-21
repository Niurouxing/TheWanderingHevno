# plugins/core_llm/__init__.py

import logging
import os
import json
from typing import List, Dict, Any, Type
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
from .factory import ProviderFactory # <-- 导入新工厂

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
def _parse_provider_configs_from_env() -> Dict[str, Dict[str, Any]]:
    """从环境变量中解析所有自定义供应商的配置。"""
    configs = {}
    provider_ids_str = os.getenv("HEVNO_LLM_PROVIDERS", "")
    if not provider_ids_str:
        return configs
        
    provider_ids = [pid.strip() for pid in provider_ids_str.split(',') if pid.strip()]

    for pid in provider_ids:
        prefix = f"PROVIDER_{pid.upper()}_"
        mapping_str = os.getenv(f"{prefix}MODEL_MAPPING", "")
        model_mapping = {}
        if mapping_str:
            try:
                model_mapping = dict(
                    item.split(":", 1) for item in mapping_str.split(",") if ":" in item
                )
            except ValueError:
                logger.warning(f"Could not parse model_mapping for {pid}: {mapping_str}")


        configs[pid] = {
            "type": os.getenv(f"{prefix}TYPE"),
            "base_url": os.getenv(f"{prefix}BASE_URL"),
            "keys_env_var": os.getenv(f"{prefix}KEYS_ENV"),
            "model_mapping": model_mapping
        }
    return configs

async def populate_llm_services(container: Container, hook_manager: HookManager):
    """
    钩子实现：现在会动态注册多个自定义供应商。
    """
    logger.debug("Async task: Populating LLM services...")
    provider_registry: ProviderRegistry = container.resolve("provider_registry")
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")

    # 1. 注册内置提供商 (保持不变)
    gemini_provider = GeminiProvider()
    provider_registry.register("gemini", gemini_provider, "GEMINI_API_KEYS")
    key_manager.register_provider("gemini", "GEMINI_API_KEYS")
    
    # 注册内置的 Mock 提供商
    mock_provider = MockProvider()
    mock_env_var = "MOCK_API_KEYS_DUMMY"
    provider_registry.register("mock", mock_provider, mock_env_var)
    key_manager.register_provider("mock", mock_env_var)

    # 2. 动态注册自定义提供商
    custom_configs = _parse_provider_configs_from_env()
    for provider_id, config in custom_configs.items():
        if not all([config["type"], config["base_url"], config["keys_env_var"]]):
            logger.warning(f"Skipping custom provider '{provider_id}' due to missing configuration.")
            continue

        # a. 为每个 provider 创建并注册一个单例工厂
        factory = ProviderFactory(initial_config=config)
        container.register(f"provider_factory_{provider_id}", lambda: factory, singleton=True)


        # b. 注册 provider 服务本身，但它不是单例！
        #    它的工厂函数从单例 ProviderFactory 中获取实例。
        #    这确保了每次解析都能拿到最新的实例。
        container.register(
            provider_id,
            lambda c, pid=provider_id: c.resolve(f"provider_factory_{pid}").get_provider(),
            singleton=False # <-- 关键！
        )

        # c. 将 provider 实例注册到 ProviderRegistry 中
        #    注意：我们在这里解析一次以完成初始注册
        try:
            provider_instance = container.resolve(provider_id)
            provider_registry.register(provider_id, provider_instance, config["keys_env_var"])
            key_manager.register_provider(provider_id, config["keys_env_var"])
            logger.info(f"Dynamically registered custom provider '{provider_id}'.")
        except Exception as e:
            logger.error(f"Failed to register custom provider '{provider_id}': {e}", exc_info=True)

    # --- 【核心修改】 ---
    # 3. 在所有提供商都注册完毕后，构建能力图谱
    provider_registry.build_capability_map()

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