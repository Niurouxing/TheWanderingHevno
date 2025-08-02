# backend/api/persistence.py

from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import io
from pydantic import ValidationError

from backend.persistence.service import PersistenceService
from backend.persistence.models import PackageManifest, PackageType, AssetType
from backend.core.state import Sandbox, SnapshotStore, StateSnapshot, GraphCollection
# 导入需要用到的依赖注入函数
from backend.persistence.service import get_persistence_service # 
from backend.core.state import get_sandbox_store, get_snapshot_store 

router = APIRouter(prefix="/api", tags=["Persistence"])

@router.get("/sandboxes/{sandbox_id}/export")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
    persistence_service: PersistenceService = Depends(get_persistence_service)
):
    """将一个沙盒及其完整历史导出为一个 .hevno.zip 文件。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox")

    # 1. 准备数据
    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    
    # 【未来扩展点】在这里调用 Stage 3 的逻辑来填充 manifest.required_plugins
    # required_plugins = scan_for_plugins(snapshots)
    # manifest.required_plugins = required_plugins

    data_files = {"sandbox.json": sandbox}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap

    # 2. 打包
    try:
        zip_bytes = persistence_service.export_package(manifest, data_files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    # 3. 返回文件流
    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox.id}.hevno.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/sandboxes/import")
async def import_sandbox(
    file: UploadFile = File(...),
    sandbox_store: Dict = Depends(get_sandbox_store),
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
    persistence_service: PersistenceService = Depends(get_persistence_service)
) -> Sandbox:
    """从一个 .hevno.zip 文件导入一个沙盒。"""
    if not file.filename.endswith(".hevno.zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .hevno.zip file.")

    zip_bytes = await file.read()
    
    try:
        manifest, data_files = persistence_service.import_package(zip_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if manifest.package_type != PackageType.SANDBOX_ARCHIVE:
        raise HTTPException(status_code=400, detail=f"Invalid package type. Expected '{PackageType.SANDBOX_ARCHIVE}', got '{manifest.package_type}'.")

    # 【未来扩展点】在这里调用 Stage 3 的逻辑来检查依赖
    # check_plugin_requirements(manifest.required_plugins)

    try:
        # 1. 恢复 Sandbox
        sandbox_data = data_files.get(manifest.entry_point)
        if not sandbox_data:
            raise ValueError(f"Entry point file '{manifest.entry_point}' not found in package.")
        
        new_sandbox = Sandbox.model_validate_json(sandbox_data)

        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with ID '{new_sandbox.id}' already exists.")

        # 2. 恢复所有 Snapshots
        for filename, content in data_files.items():
            if filename.startswith("snapshots/"):
                snapshot = StateSnapshot.model_validate_json(content)
                snapshot_store.save(snapshot) # 假设 save 内部会检查重复
        
        # 3. 保存 Sandbox
        sandbox_store[new_sandbox.id] = new_sandbox
        return new_sandbox

    except (ValidationError, ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {e}")

# (为简洁起见，资产管理器的 API 暂时省略，但其实现将与上述类似)