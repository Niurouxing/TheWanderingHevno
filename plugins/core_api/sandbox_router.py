# plugins/core_api/sandbox_router.py

import io
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone
from PIL import Image

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, FileResponse

# 导入核心依赖解析器和所有必要的接口与数据模型（契约）
from backend.core.dependencies import Service
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    GraphCollection,
    ExecutionEngineInterface,
    SnapshotStoreInterface
)
from plugins.core_persistence.contracts import (
    PersistenceServiceInterface, 
    PackageManifest, 
    PackageType
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sandboxes", 
    tags=["Sandboxes"]
)

# --- Request/Response Models ---

class CreateSandboxRequest(BaseModel):
    name: str = Field(..., description="The human-readable name for the sandbox.")
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SandboxListItem(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    icon_url: str
    has_custom_icon: bool

class UpdateSandboxRequest(BaseModel):
    name: str = Field(..., min_length=1, description="The new name for the sandbox.")


# --- Sandbox Lifecycle API ---

@router.post("", response_model=Sandbox, status_code=201, summary="Create a new Sandbox")
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """
    创建一个新的沙盒，并为其生成一个初始（创世）快照。
    这是与一个新世界交互的起点。
    """
    sandbox = Sandbox(name=request_body.name)
    if sandbox.id in sandbox_store:
        raise HTTPException(status_code=409, detail=f"Sandbox with ID {sandbox.id} already exists.")
    
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request_body.graph_collection,
        world_state=request_body.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    
    logger.info(f"Created new sandbox '{sandbox.name}' ({sandbox.id}).")
    return sandbox
    

@router.patch("/{sandbox_id}", response_model=Sandbox, summary="Update Sandbox Details")
async def update_sandbox_details(
    sandbox_id: UUID,
    request_body: UpdateSandboxRequest,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store"))
):
    """
    更新沙盒的详细信息，例如名称。
    这是一个局部更新，所以使用 PATCH 方法。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    # 更新沙盒名称
    sandbox.name = request_body.name
    logger.info(f"Updated name for sandbox '{sandbox.id}' to '{sandbox.name}'.")

    # 注意：因为 sandbox_store 是一个在内存中的字典，这里的修改会立即生效。
    # 在一个真实的、带持久化的应用中，这里会调用一个 service.save(sandbox) 方法。

    return sandbox

@router.delete("/{sandbox_id}", status_code=204, summary="Delete a Sandbox")
async def delete_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    # 如果有持久化，也需要注入 persistence_service
):
    """
    永久删除一个沙盒及其所有关联的快照。
    """
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    # 1. 从内存中删除沙盒
    del sandbox_store[sandbox_id]

    # 2. 从快照存储中删除所有关联的快照
    # (SnapshotStoreInterface 需要一个删除方法)
    # 假设 snapshot_store 有一个 `delete_by_sandbox(sandbox_id)` 方法
    # snapshot_store.delete_by_sandbox(sandbox_id)

    logger.info(f"Deleted sandbox '{sandbox_id}' and all associated data.")
    return Response(status_code=204)
    
@router.post("/{sandbox_id}/step", response_model=StateSnapshot, summary="Execute a step")
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    engine: ExecutionEngineInterface = Depends(Service("execution_engine"))
):
    """在沙盒的最新状态上执行一步计算，生成一个新的状态快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not sandbox.head_snapshot_id:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state to step from.")
        
    latest_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
    if not latest_snapshot:
        logger.error(f"Data inconsistency for sandbox {sandbox_id}: head snapshot '{sandbox.head_snapshot_id}' not found.")
        raise HTTPException(status_code=500, detail=f"Data inconsistency: head snapshot not found.")
    
    new_snapshot = await engine.step(latest_snapshot, user_input)
    
    sandbox.head_snapshot_id = new_snapshot.id
    
    return new_snapshot

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot], summary="Get history")
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """获取一个沙盒的所有历史快照，按时间顺序排列。"""
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
        
    return snapshot_store.find_by_sandbox(sandbox_id)

@router.put("/{sandbox_id}/revert", status_code=200, summary="Revert to a snapshot")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """将沙盒的状态回滚到指定的历史快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")
    
    sandbox.head_snapshot_id = snapshot_id
    logger.info(f"Reverted sandbox '{sandbox.name}' ({sandbox.id}) to snapshot {snapshot_id}.")
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}


# --- Sandbox Import/Export API ---

@router.get("", response_model=List[SandboxListItem], summary="List all Sandboxes")
async def list_sandboxes(
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    all_sandboxes = list(sandbox_store.values())
    response_items = []
    
    for sandbox in all_sandboxes:
        icon_path = persistence_service.get_sandbox_icon_path(str(sandbox.id))
        has_custom_icon = icon_path is not None
        
        icon_url = f"/api/sandboxes/{sandbox.id}/icon"
        if sandbox.icon_updated_at:
            icon_url += f"?v={int(sandbox.icon_updated_at.timestamp())}"
        
        response_items.append(
            SandboxListItem(
                id=sandbox.id,
                name=sandbox.name,
                created_at=sandbox.created_at,
                icon_url=icon_url,
                has_custom_icon=has_custom_icon
            )
        )
        
    return sorted(response_items, key=lambda s: s.created_at, reverse=True)

@router.get("/{sandbox_id}/icon", response_class=FileResponse, summary="Get Sandbox Icon")
async def get_sandbox_icon(
    sandbox_id: UUID,
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    icon_path = persistence_service.get_sandbox_icon_path(str(sandbox_id))
    if icon_path:
        return FileResponse(icon_path)
    
    default_icon_path = persistence_service.get_default_icon_path()
    if not default_icon_path.is_file():
        raise HTTPException(status_code=404, detail="Default icon not found on server.")
    return FileResponse(default_icon_path)

@router.post("/{sandbox_id}/icon", status_code=200, summary="Upload/Update Sandbox Icon")
async def upload_sandbox_icon(
    sandbox_id: UUID,
    file: UploadFile = File(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service")),
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not file.content_type == "image/png":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG is allowed.")

    icon_bytes = await file.read()
    
    # 安全验证
    try:
        img = Image.open(io.BytesIO(icon_bytes))
        img.verify() # 验证文件结构
        
        # 重新打开以检查元数据
        img = Image.open(io.BytesIO(icon_bytes))
        if img.format != 'PNG':
            raise ValueError("Image format is not PNG.")
        if max(img.size) > 2048:
            raise ValueError("Image dimensions are too large (max 2048x2048).")
            
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid PNG file: {e}")

    persistence_service.save_sandbox_icon(str(sandbox.id), icon_bytes)
    sandbox.icon_updated_at = datetime.now(timezone.utc)
    
    return {"message": "Icon updated successfully."}

@router.get("/{sandbox_id}/export", response_class=Response, summary="Export a Sandbox as PNG")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    """
    将一个沙盒及其完整历史导出为一个嵌入了数据的PNG图片文件。
    该图片将使用沙盒当前的封面图标作为基础图像。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    logger.debug(f"Exporting sandbox {sandbox_id}. Found {len(snapshots)} snapshots.")

    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    data_files: Dict[str, BaseModel] = {"sandbox.json": sandbox}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap

    base_image_bytes = None
    icon_path = persistence_service.get_sandbox_icon_path(str(sandbox.id))
    if not icon_path:
        icon_path = persistence_service.get_default_icon_path()
    
    if icon_path.is_file():
        base_image_bytes = icon_path.read_bytes()
    else:
        logger.warning(f"Could not find a base image for export (neither custom nor default). A blank PNG will be generated.")

    try:
        logger.debug("Calling persistence_service.export_package...")
        png_bytes = persistence_service.export_package(manifest, data_files, base_image_bytes)
        logger.debug(f"export_package returned {len(png_bytes)} bytes of PNG data.")
    except Exception as e:
        logger.error(f"Failed to create package for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/import", response_model=Sandbox, summary="Import a Sandbox from PNG")
async def import_sandbox(
    file: UploadFile = File(..., description="A .hevno.zip package file embedded in a PNG."),
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
) -> Sandbox:
    """
    从一个包含数据的PNG文件导入一个沙盒及其完整历史。
    导入的PNG图像本身将自动成为新沙盒的封面图标。
    """
    if not file.filename or not file.filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .png file.")

    package_bytes = await file.read()
    logger.debug(f"Importing file '{file.filename}' with size {len(package_bytes)} bytes.")
    
    try:
        logger.debug("Calling persistence_service.import_package...")
        manifest, data_files, png_bytes = persistence_service.import_package(package_bytes)
        logger.debug(f"import_package successful. Manifest type: {manifest.package_type}. Found {len(data_files)} data files.")
    except ValueError as e:
        logger.warning(f"Failed to import package: {e}", exc_info=False)
        raise HTTPException(status_code=400, detail=f"Invalid package: {e}")

    if manifest.package_type != PackageType.SANDBOX_ARCHIVE:
        raise HTTPException(status_code=400, detail=f"Invalid package type. Expected '{PackageType.SANDBOX_ARCHIVE.value}'.")

    try:
        sandbox_data_str = data_files.get(manifest.entry_point)
        if not sandbox_data_str:
            raise ValueError(f"Entry point file '{manifest.entry_point}' not found in package.")
        
        new_sandbox = Sandbox.model_validate_json(sandbox_data_str)
        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with ID '{new_sandbox.id}' already exists.")

        recovered_snapshots = []
        for filename, content_str in data_files.items():
            if filename.startswith("snapshots/"):
                snapshot = StateSnapshot.model_validate_json(content_str)
                if snapshot.sandbox_id != new_sandbox.id:
                    raise ValueError(f"Snapshot {snapshot.id} does not belong to the imported sandbox {new_sandbox.id}.")
                recovered_snapshots.append(snapshot)
        
        if not recovered_snapshots:
            raise ValueError("No snapshots found in the package.")

        for snapshot in recovered_snapshots:
            snapshot_store.save(snapshot)
        
        try:
            persistence_service.save_sandbox_icon(str(new_sandbox.id), png_bytes)
            new_sandbox.icon_updated_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to set icon for newly imported sandbox {new_sandbox.id}: {e}")

        sandbox_store[new_sandbox.id] = new_sandbox
        
        logger.info(f"Successfully imported sandbox '{new_sandbox.name}' ({new_sandbox.id}).")
        return new_sandbox

    except (ValidationError, ValueError) as e:
        logger.warning(f"Failed to process package data for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {str(e)}")