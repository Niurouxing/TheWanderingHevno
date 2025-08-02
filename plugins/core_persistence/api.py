# plugins/core_persistence/api.py

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
import io

from .service import PersistenceService
from .models import PackageManifest, PackageType

# 注意：为了解耦，我们不从其他插件导入模型，如 Sandbox 或 StateSnapshot
# 在实际的 API 实现中，我们将处理原始的字典或 Pydantic BaseModel

logger = logging.getLogger(__name__)

# --- 依赖注入函数 ---
# 这个函数定义了如何为请求获取 PersistenceService 实例
def get_persistence_service(request: Request) -> PersistenceService:
    # 从 app.state 获取容器，然后解析服务
    return request.app.state.container.resolve("persistence_service")

# --- API 路由 ---
router = APIRouter(prefix="/api/persistence", tags=["Core-Persistence"])

@router.get("/assets")
async def list_all_assets(
    # service: PersistenceService = Depends(get_persistence_service) # 示例
):
    # 这里的逻辑需要根据您希望如何列出资产来具体实现
    # 例如：service.list_assets(...)
    return {"message": "Asset listing endpoint for core_persistence."}


# 导入/导出功能可以像旧的 api/persistence.py 一样实现
# 这里只给出一个示例以展示路由的创建
@router.post("/package/import")
async def import_package(
    file: UploadFile = File(...),
    service: PersistenceService = Depends(get_persistence_service)
):
    logger.info(f"Received package for import: {file.filename}")
    if not file.filename.endswith(".hevno.zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .hevno.zip file.")
    
    zip_bytes = await file.read()
    try:
        manifest, _ = service.import_package(zip_bytes)
        # 在这里，我们可以根据 manifest 的内容，触发其他钩子来处理导入的数据
        # 例如: await hook_manager.trigger("sandbox_imported", manifest=manifest, data=data_files)
        logger.info(f"Successfully parsed package '{manifest.package_type}' created at {manifest.created_at}")
        return manifest
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))