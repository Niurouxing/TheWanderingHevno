# plugins/core_persistence/api.py

import logging
from typing import List
from fastapi import APIRouter, Depends

# 从本插件内部导入所需的组件
from .service import PersistenceService
from .models import AssetType
from .dependencies import get_persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/persistence", 
    tags=["Core-Persistence"]
)

@router.get("/assets/{asset_type}", response_model=List[str])
async def list_assets_by_type(
    asset_type: AssetType,
    service: PersistenceService = Depends(get_persistence_service)
):
    """
    列出指定类型的所有已保存资产的名称。
    例如，要列出所有图，可以请求 GET /api/persistence/assets/graph
    """
    try:
        return service.list_assets(asset_type)
    except Exception as e:
        logger.error(f"Failed to list assets of type '{asset_type.value}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while listing assets.")

# 注意：通用的 /package/import 端点被移除了，因为导入总是与特定资源（如沙盒）相关。
# 直接在特定资源的 API 中处理导入逻辑更符合 RESTful 原则。