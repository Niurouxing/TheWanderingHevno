# plugins/core_persistence/api.py

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from .service import PersistenceService
from .models import AssetType
from .dependencies import get_persistence_service

logger = logging.getLogger(__name__)

# --- Router for persistence API ---
persistence_router = APIRouter(
    prefix="/api/persistence", 
    tags=["Core-Persistence"]
)

@persistence_router.get("/assets/{asset_type}", response_model=List[str])
async def list_assets_by_type(
    asset_type: AssetType,
    service: PersistenceService = Depends(get_persistence_service)
):
    """
    列出指定类型的所有已保存资产的名称。
    """
    try:
        return service.list_assets(asset_type)
    except Exception as e:
        logger.error(f"Failed to list assets of type '{asset_type.value}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while listing assets.")