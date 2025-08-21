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


logger = logging.getLogger(__name__)

config_api_router = APIRouter(
    prefix="/api/llm/config",
    tags=["LLM Configuration API"]
)

# --- Pydantic Models (保持不变) ---
class ApiKeyStatus(BaseModel):
    key_suffix: str
    status: str
    rate_limit_until: Optional[float] = None

class KeyConfigResponse(BaseModel):
    provider: str
    keys: List[ApiKeyStatus]

# --- [新] Pydantic Model for Add Key ---
class AddKeyRequest(BaseModel):
    key: str = Field(..., min_length=10, description="要添加的完整 API 密钥。")

# --- 新的 Pydantic 模型 ---
class CustomProviderConfig(BaseModel):
    base_url: Optional[str] = Field(None, description="自定义提供商的基础URL (例如 'https://api.example.com')。")
    model_mapping: Optional[str] = Field(
        None, 
        description="模型映射。格式为 'proxy_model_name:real_model_name,another:real' 或 JSON 字符串 '{"proxy":"real"}'。"
    )

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

@config_api_router.post("/reload", status_code=200)
async def reload_llm_configuration(
    container: Container = Depends(Service("container"))
):
    """
    从 .env 文件重新加载所有 LLM 供应商配置，并热更新服务，无需重启。
    """
    try:
        logger.info("--- Initiating LLM configuration hot reload ---")
        
        # 1. 重新加载环境变量
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv(), override=True)

        # 2. 重新解析配置
        new_configs = _parse_provider_configs_from_env()
        
        provider_registry: ProviderRegistry = container.resolve("provider_registry")
        key_manager: KeyPoolManager = container.resolve("key_pool_manager")

        # 3. 更新或创建工厂
        for provider_id, config in new_configs.items():
            factory_name = f"provider_factory_{provider_id}"
            try:
                # 尝试获取已存在的工厂并更新它
                factory: ProviderFactory = container.resolve(factory_name)
                factory.update_config_and_recreate(config)
                logger.info(f"Updated and recreated provider '{provider_id}'.")
            except ValueError:
                # 工厂不存在，说明是新添加的供应商
                logger.warning(f"Provider '{provider_id}' appears to be new. A full application restart is recommended for new providers.")
                # 在这种简化模式下，我们不动态添加全新的provider，只更新现有的
                continue

            # 4. 重新填充 ProviderRegistry 和 KeyPoolManager
            new_instance = container.resolve(provider_id) # 这会从工厂获取新实例
            provider_registry.register(provider_id, new_instance, config["keys_env_var"])
            key_manager.register_provider(provider_id, config["keys_env_var"])
        
        logger.info("--- LLM configuration hot reload completed ---")
        return {"message": "LLM configuration reloaded successfully."}
    except Exception as e:
        logger.exception("Failed during LLM configuration hot reload.")
        raise HTTPException(status_code=500, detail=str(e))


# --- [新] 自定义提供商配置的 API 端点 ---

@config_api_router.get("/custom_provider", response_model=CustomProviderConfig)
async def get_custom_provider_configuration(
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    """获取当前配置的自定义OpenAI兼容提供商的设置。"""
    config = key_manager.get_custom_provider_config()
    return CustomProviderConfig(**config)

@config_api_router.put("/custom_provider", status_code=200)
async def update_custom_provider_configuration(
    request: CustomProviderConfig,
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    """
    更新或设置自定义提供商的配置。
    提供空值可以删除配置项。
    注意：此操作会触发所有LLM提供商的密钥池重新加载。
    """
    try:
        key_manager.set_custom_provider_config(request.base_url, request.model_mapping)
        # 警告：这里不能直接重新加载服务，因为服务是单例。
        # 应用需要被设计为能够处理这种动态配置变化，或者需要重启。
        # 我们的设计通过重新加载密钥池已经部分实现了这一点。
        return {"message": "Custom provider configuration updated. The application will use the new settings on subsequent reloads."}
    except Exception as e:
        logger.exception("Failed to update custom provider config.")
        raise HTTPException(status_code=500, detail=str(e))


# --- API Endpoints (重构后) ---

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
