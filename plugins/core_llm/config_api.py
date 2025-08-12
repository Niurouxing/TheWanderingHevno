# plugins/core_llm/config_api.py

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException

from backend.core.dependencies import Service
from .manager import KeyPoolManager, KeyInfo, ProviderKeyPool

logger = logging.getLogger(__name__)

config_api_router = APIRouter(
    prefix="/api/llm/config",
    tags=["LLM Configuration API"]
)

# --- Pydantic Models for API ---

class ApiKeyStatus(BaseModel):
    """安全地表示一个 API 密钥的状态，不暴露完整密钥。"""
    key_suffix: str = Field(..., description="密钥的最后4位。")
    status: str
    rate_limit_until: Optional[float] = None

class KeyConfigResponse(BaseModel):
    provider: str
    keys: List[ApiKeyStatus]

class UpdateKeysRequest(BaseModel):
    keys: List[str] = Field(..., description="要使用的新 API 密钥的完整列表。")

# --- API Endpoints ---

# --- [核心修复] ---
# 我们需要告诉 FastAPI 如何为这个辅助函数提供 key_manager
def get_key_pool(
    provider_name: str, 
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager")) # <-- 添加 Depends
) -> ProviderKeyPool:
    """FastAPI 依赖项，用于获取特定提供商的密钥池。"""
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
    """获取指定提供商的所有密钥及其当前状态。"""
    key_statuses = []
    # key_pool._keys 是一个实现细节，但对于配置API是可接受的
    for key_info in key_pool._keys:
        key_statuses.append(ApiKeyStatus(
            key_suffix=f"...{key_info.key_string[-4:]}",
            status=key_info.status.value,
            rate_limit_until=key_info.rate_limit_until if key_info.rate_limit_until > 0 else None
        ))
    return KeyConfigResponse(provider=provider_name, keys=key_statuses)


@config_api_router.put("/{provider_name}", status_code=200)
async def update_provider_keys(
    provider_name: str,
    request: UpdateKeysRequest,
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    """
    在内存中更新一个提供商的 API 密钥。
    注意：这些更改在服务器重启后会丢失。
    """
    try:
        # 我们需要在 KeyPoolManager 中添加一个方法来支持此操作
        key_manager.update_provider_keys(provider_name, request.keys)
        logger.info(f"In-memory keys for provider '{provider_name}' updated successfully.")
        return {"message": f"Keys for provider '{provider_name}' have been updated in memory."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception(f"Failed to update keys for provider {provider_name}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")