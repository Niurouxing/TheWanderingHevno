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

@config_api_router.post("/{provider_name}/keys", status_code=201)
async def add_provider_key(
    provider_name: str,
    request: AddKeyRequest,
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    """向 .env 文件添加一个新的 API 密钥并重新加载。"""
    try:
        key_manager.add_key_to_provider(provider_name, request.key)
        return {"message": "Key added successfully and pool reloaded."}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception(f"Failed to add key for provider {provider_name}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@config_api_router.delete("/{provider_name}/keys/{key_suffix}", status_code=200)
async def remove_provider_key(
    provider_name: str,
    key_suffix: str,
    key_manager: KeyPoolManager = Depends(Service("key_pool_manager"))
):
    """从 .env 文件中删除一个 API 密钥并重新加载。"""
    if len(key_suffix) != 4:
        raise HTTPException(status_code=400, detail="Key suffix must be exactly 4 characters long.")
    try:
        key_manager.remove_key_from_provider(provider_name, key_suffix)
        return {"message": "Key removed successfully and pool reloaded."}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception(f"Failed to remove key for provider {provider_name}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")