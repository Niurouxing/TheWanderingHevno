# plugins/core_persistence/api.py

import logging
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

# 从本插件内部导入所需的组件
from .service import PersistenceService
from .models import AssetType
from .dependencies import get_persistence_service

logger = logging.getLogger(__name__)

# --- Router 1: 用于现有的持久化 API ---
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
    例如，要列出所有图，可以请求 GET /api/persistence/assets/graph
    """
    try:
        return service.list_assets(asset_type)
    except Exception as e:
        logger.error(f"Failed to list assets of type '{asset_type.value}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while listing assets.")

# --- Router 2: 【新功能】用于动态服务前端插件的静态资源 ---
frontend_assets_router = APIRouter(
    tags=["System", "Frontend Assets"]
)

# 计算出项目根目录下的 'plugins' 文件夹路径
# api.py 位于 plugins/core_persistence/api.py
# .parent -> plugins/core_persistence
# .parent.parent -> plugins
PLUGINS_DIR = Path(__file__).resolve().parent.parent

@frontend_assets_router.get("/plugins/{plugin_id}/{resource_path:path}")
async def serve_plugin_resource(plugin_id: str, resource_path: str):
    """
    动态服务任何前端插件的任何静态资源。
    此端点会将 /plugins/{id}/{path} 映射到服务器上的 [PROJECT_ROOT]/plugins/{id}/{path} 文件。
    """
    try:
        # 安全性：简单清理，防止基本的路径遍历尝试
        if ".." in plugin_id or "\\" in plugin_id:
            raise HTTPException(status_code=400, detail="Invalid plugin ID.")
        
        # 1. 构建目标文件的绝对路径
        plugin_base_path = (PLUGINS_DIR / plugin_id).resolve()
        target_file_path = (plugin_base_path / resource_path).resolve()

        # 2. 安全性：验证解析后的路径是否仍在合法的插件目录内，防止路径遍历攻击
        if not str(target_file_path).startswith(str(plugin_base_path)):
            logger.warning(f"Forbidden access attempt: {plugin_id}/{resource_path}")
            raise HTTPException(status_code=403, detail="Forbidden: Access outside of plugin directory is not allowed.")

        # 3. 检查文件是否存在
        if not target_file_path.is_file():
            logger.debug(f"Frontend resource not found at path: {target_file_path}")
            raise HTTPException(status_code=404, detail=f"Resource '{resource_path}' not found in plugin '{plugin_id}'.")

        # 4. 返回文件响应，FastAPI 会自动处理 Content-Type
        return FileResponse(target_file_path)

    except HTTPException as e:
        # 重新抛出已知的 HTTP 异常
        raise e
    except Exception as e:
        logger.error(f"Error serving plugin resource '{plugin_id}/{resource_path}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while serving plugin resource.")