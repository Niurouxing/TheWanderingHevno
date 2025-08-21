# plugins/core_llm/config_api.py

import logging
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException

from backend.core.dependencies import Service
from backend.core.contracts import Container
from .manager import KeyPoolManager, KeyInfo, ProviderKeyPool
from .factory import ProviderFactory
from .registry import ProviderRegistry
from .utils import parse_provider_configs_from_env
# [新增] 导入 LLMProvider 基类以进行类型提示
from .providers.base import LLMProvider


logger = logging.getLogger(__name__)

config_api_router = APIRouter(
    prefix="/api/llm/config",
    tags=["LLM Configuration API"]
)


class ApiKeyStatus(BaseModel):
    key_suffix: str
    status: str
    rate_limit_until: Optional[float] = None

class KeyConfigResponse(BaseModel):
    provider: str
    keys: List[ApiKeyStatus]

class AddKeyRequest(BaseModel):
    key: str = Field(..., min_length=10, description="要添加的完整 API 密钥。")

# [新增] 为新的 /providers 端点定义响应模型
class ProviderInfo(BaseModel):
    id: str
    type: str # 'gemini', 'mock', 'openai_compatible' 等
    model_mapping: Dict[str, str] = Field(default_factory=dict)
    
class ProvidersListResponse(BaseModel):
    providers: List[ProviderInfo]


# --- API 端点 ---

# 端点：获取所有已注册的提供商信息
@config_api_router.get("/providers", response_model=ProvidersListResponse)
async def list_registered_providers(
    provider_registry: ProviderRegistry = Depends(Service("provider_registry"))
):
    """
    获取后端当前已注册的所有 LLM 提供商的列表及其元数据。
    """
    provider_infos = []
    for provider_id in provider_registry.get_all_provider_names():
        provider_instance: LLMProvider = provider_registry.get(provider_id)
        if provider_instance:
            provider_infos.append(ProviderInfo(
                id=provider_id,
                type=provider_instance.__class__.__name__, # e.g., "GeminiProvider"
                # 假设所有 provider 都有 model_mapping 属性，没有则为空字典
                model_mapping=getattr(provider_instance, 'model_mapping', {})
            ))
    return ProvidersListResponse(providers=provider_infos)


@config_api_router.post("/reload", status_code=200)
async def reload_llm_configuration(
    container: Container = Depends(Service("container"))
):
    """热重载 LLM 提供商配置（处理更新、新增、移除）。"""
    try:
        logger.info("--- Initiating LLM configuration hot reload ---")
        
        provider_registry: ProviderRegistry = container.resolve("provider_registry")
        key_manager: KeyPoolManager = container.resolve("key_pool_manager")

        built_in_providers = {"gemini", "mock"}
        old_custom_provider_ids = set(provider_registry.get_all_provider_names()) - built_in_providers

        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv(), override=True)

        new_configs = parse_provider_configs_from_env()
        new_custom_provider_ids = set(new_configs.keys())
        
        removed_ids = old_custom_provider_ids - new_custom_provider_ids
        if removed_ids:
            logger.info(f"Providers to be removed: {removed_ids}")
            for provider_id in removed_ids:
                provider_registry.unregister(provider_id)
                key_manager.unregister_provider(provider_id)
                logger.warning(f"Provider '{provider_id}' has been unregistered. Its factory remains in the DI container but will be inactive.")
        
        for provider_id, config in new_configs.items():
            factory_name = f"provider_factory_{provider_id}"
            try:
                factory: ProviderFactory = container.resolve(factory_name)
                factory.update_config_and_recreate(config)
                logger.info(f"Updated and recreating provider '{provider_id}'.")
            except ValueError:
                logger.info(f"Provider '{provider_id}' is new. Dynamically creating its factory and services.")
                factory = ProviderFactory(initial_config=config)
                container.register(factory_name, lambda: factory, singleton=True)
                container.register(
                    provider_id,
                    lambda c, pid=provider_id: c.resolve(f"provider_factory_{pid}").get_provider(),
                    singleton=False
                )

            new_instance = container.resolve(provider_id)
            provider_registry.register(provider_id, new_instance, config["keys_env_var"])
            key_manager.register_provider(provider_id, config["keys_env_var"])
        
        provider_registry.build_capability_map()

        logger.info("--- LLM configuration hot reload completed ---")
        return {"message": "LLM configuration reloaded successfully."}
    except Exception as e:
        logger.exception("Failed during LLM configuration hot reload.")
        raise HTTPException(status_code=500, detail=str(e))



# [新增] 添加和删除密钥的API端点
@config_api_router.post("/{provider_name}/keys", status_code=201)
async def add_api_key(
    provider_name: str,
    request: AddKeyRequest,
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    try:
        key_manager.add_key_to_provider(provider_name, request.key)
        return {"message": f"Key successfully added to provider '{provider_name}' and .env file updated."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add key: {e}")

@config_api_router.delete("/{provider_name}/keys/{key_suffix}", status_code=200)
async def delete_api_key(
    provider_name: str,
    key_suffix: str,
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    try:
        key_manager.remove_key_from_provider(provider_name, key_suffix)
        return {"message": f"Key ending in '...{key_suffix}' for provider '{provider_name}' removed from .env file."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove key: {e}")


def get_key_pool(
    provider_name: str, 
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
) -> ProviderKeyPool:
    pool = key_manager.get_pool(provider_name)
    if not pool:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider_name}' not found or has no key pool registered."
        )
    return pool

@config_api_router.get("/{provider_name}", response_model=KeyConfigResponse)
async def get_key_configuration(
    provider_name: str,
    key_pool: ProviderKeyPool = Depends(get_key_pool)
):
    key_statuses = []
    for key_info in key_pool._keys:
        key_statuses.append(ApiKeyStatus(
            key_suffix=f"...{key_info.key_string[-4:]}",
            status=key_info.status.value,
            rate_limit_until=key_info.rate_limit_until if key_info.rate_limit_until > 0 else None
        ))
    return KeyConfigResponse(provider=provider_name, keys=key_statuses)
