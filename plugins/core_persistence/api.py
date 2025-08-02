# plugins/core_persistence/api.py

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

# 从本插件内部导入所需的组件
from .service import PersistenceService
from .models import AssetType, PackageManifest
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
        asset_names = service.list_assets(asset_type)
        return asset_names
    except Exception as e:
        logger.error(f"Failed to list assets of type '{asset_type.value}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while listing assets.")

@router.post("/package/import", response_model=PackageManifest)
async def import_package(
    file: UploadFile = File(..., description="A .hevno.zip package file."),
    service: PersistenceService = Depends(get_persistence_service)
):
    """
    上传并解析一个 .hevno.zip 包文件。
    
    此端点负责验证包的结构并返回其清单 (manifest)。
    它不负责将包的内容（如沙盒或图）实际加载到引擎中。
    这一过程应由监听 'package_imported' 等钩子的其他插件来完成。
    """
    logger.info(f"Received package for import: {file.filename}")
    if not file.filename or not file.filename.endswith(".hevno.zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .hevno.zip file.")

    zip_bytes = await file.read()
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        # PersistenceService 负责解压和解析
        manifest, data_files = service.import_package(zip_bytes)
        
        # TODO: (设计决策) 在这里触发一个钩子，让其他插件可以响应这次导入。
        # hook_manager = request.app.state.container.resolve("hook_manager")
        # await hook_manager.trigger(
        #     "package_imported", 
        #     manifest=manifest, 
        #     data_files=data_files
        # )
        
        logger.info(f"Successfully parsed package '{manifest.package_type}' created at {manifest.created_at}")
        return manifest
        
    except ValueError as e:
        logger.warning(f"Failed to import package '{file.filename}': {e}")
        raise HTTPException(status_code=400, detail=f"Invalid package: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during package import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during package import.")

# 注意：
# 沙盒的导出/导入 API (如 /api/sandboxes/{id}/export) 已被正确地
# 放置在 core_api 插件的 sandbox_router.py 中，因为它与 'sandbox' 资源紧密相关，
# 并且需要编排来自多个服务（snapshot_store, persistence_service）的数据。
# 这种分离保持了此插件的通用性和低耦合性。