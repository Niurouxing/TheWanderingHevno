# plugins/core_engine/api.py

import io
import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError, field_validator
from datetime import datetime, timezone
from PIL import Image

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response, FileResponse, JSONResponse

# 导入核心依赖解析器和所有必要的接口与数据模型（契约）
from backend.core.dependencies import Service
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    ExecutionEngineInterface,
    SnapshotStoreInterface
)
from plugins.core_persistence.contracts import (
    PersistenceServiceInterface, 
    PackageManifest, 
    PackageType
)
# 导入新的持久化存储类以进行类型提示，增强代码可读性
from plugins.core_persistence.stores import PersistentSandboxStore

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sandboxes", 
    tags=["Sandboxes"]
)

# --- Request/Response Models ---

class CreateSandboxRequest(BaseModel):
    name: str = Field(..., description="沙盒的人类可读名称。")
    definition: Dict[str, Any] = Field(
        ..., 
        description="沙盒的'设计蓝图'，必须包含 'initial_lore' 和 'initial_moment' 键。"
    )
    @field_validator('definition')
    @classmethod
    def check_definition_structure(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if "initial_lore" not in v or "initial_moment" not in v:
            raise ValueError("Definition must contain 'initial_lore' and 'initial_moment' keys.")
        return v

class SandboxListItem(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    icon_url: str
    has_custom_icon: bool

class UpdateSandboxRequest(BaseModel):
    name: str = Field(..., min_length=1, description="沙盒的新名称。")

class SandboxArchiveJSON(BaseModel):
    sandbox: Sandbox
    snapshots: List[StateSnapshot]

# --- Sandbox Lifecycle API ---

@router.post("", response_model=Sandbox, status_code=201, summary="Create a new Sandbox")
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """
    创建一个新的沙盒，并将其立即持久化到本地文件系统。
    """
    initial_lore = request_body.definition.get("initial_lore", {})
    initial_moment = request_body.definition.get("initial_moment", {})
    
    sandbox = Sandbox(
        name=request_body.name,
        definition=request_body.definition,
        lore=initial_lore
    )
    if sandbox.id in sandbox_store:
        raise HTTPException(status_code=409, detail=f"Sandbox with ID {sandbox.id} already exists.")
    
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        moment=initial_moment
    )
    await snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    
    await sandbox_store.save(sandbox)
    
    logger.info(f"Created new sandbox '{sandbox.name}' ({sandbox.id}) and saved to disk.")
    return sandbox


@router.post("/{sandbox_id}/step", response_model=Sandbox, summary="Execute a step")
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    engine: ExecutionEngineInterface = Depends(Service("execution_engine"))
):
    """
    执行一步计算。持久化逻辑已封装在 engine.step 方法内部。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    try:
        updated_sandbox = await engine.step(sandbox, user_input)
    except Exception as e:
        logger.error(f"Error during engine step for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Engine execution failed: {e}")

    return updated_sandbox


@router.put("/{sandbox_id}/revert", status_code=200, summary="Revert to a snapshot")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID = Body(..., embed=True),
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    """
    将沙盒的状态回滚到指定的历史快照。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    # 如果缓存里没有，就从磁盘加载所有快照来确认它是否存在
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        all_snapshots = await snapshot_store.find_by_sandbox(sandbox_id)
        if not any(s.id == snapshot_id for s in all_snapshots):
            raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")

    sandbox.head_snapshot_id = snapshot_id
    
    await sandbox_store.save(sandbox)
    
    logger.info(f"Reverted sandbox '{sandbox.name}' ({sandbox.id}) to snapshot {snapshot_id} and saved.")
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}


# --- 其他端点 ---

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot], summary="Get history")
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return await snapshot_store.find_by_sandbox(sandbox_id)


@router.patch("/{sandbox_id}", response_model=Sandbox, summary="Update Sandbox Details")
async def update_sandbox_details(
    sandbox_id: UUID,
    request_body: UpdateSandboxRequest,
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    sandbox.name = request_body.name
    
    await sandbox_store.save(sandbox)
    
    logger.info(f"Updated name for sandbox '{sandbox.id}' to '{sandbox.name}' and saved.")
    return sandbox


@router.delete("/{sandbox_id}", status_code=204, summary="Delete a Sandbox")
async def delete_sandbox(
    sandbox_id: UUID,
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
):
    """
    从文件系统和缓存中完全删除一个沙盒及其所有数据。
    """
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    await sandbox_store.delete(sandbox_id)
    
    logger.info(f"Deleted sandbox '{sandbox_id}' and all associated data from disk.")
    return Response(status_code=204)


@router.get("", response_model=List[SandboxListItem], summary="List all Sandboxes")
async def list_sandboxes(
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    # sandbox_store.values() 从缓存读取，是同步的
    all_sandboxes = sandbox_store.values()
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

# --- Icon, Export, Import 端点 ---

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
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service")),
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    if not file.content_type == "image/png":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG is allowed.")

    icon_bytes = await file.read()
    
    try:
        img = Image.open(io.BytesIO(icon_bytes))
        img.verify() 
        img = Image.open(io.BytesIO(icon_bytes))
        if img.format != 'PNG':
            raise ValueError("Image format is not PNG.")
        if max(img.size) > 2048:
            raise ValueError("Image dimensions are too large (max 2048x2048).")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid PNG file: {e}")

    # 添加 await 调用异步方法
    await persistence_service.save_sandbox_icon(str(sandbox.id), icon_bytes)
    sandbox.icon_updated_at = datetime.now(timezone.utc)
    
    await sandbox_store.save(sandbox)
    
    return {"message": "Icon updated successfully."}


@router.get(
    "/{sandbox_id}/export/json", 
    response_class=JSONResponse, 
    summary="Export a Sandbox as JSON"
)
async def export_sandbox_json(
    sandbox_id: UUID,
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    # 添加 await 调用异步方法
    snapshots = await snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    archive = SandboxArchiveJSON(sandbox=sandbox, snapshots=snapshots)
    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.json"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return JSONResponse(content=archive.model_dump(mode="json"), headers=headers)


@router.post(
    "/import/json", 
    response_model=Sandbox, 
    status_code=201, 
    summary="Import a Sandbox from JSON"
)
async def import_sandbox_json(
    file: UploadFile = File(...),
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
) -> Sandbox:
    if not file.content_type == "application/json":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .json file.")

    try:
        content = await file.read()
        data = json.loads(content)
        archive = SandboxArchiveJSON.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid sandbox archive format: {e}")

    old_sandbox_id = archive.sandbox.id
    new_sandbox_id = uuid.uuid4()
    snapshot_id_map = {snap.id: uuid.uuid4() for snap in archive.snapshots}
    
    for old_snapshot in archive.snapshots:
        new_snapshot = old_snapshot.model_copy(update={
            'id': snapshot_id_map[old_snapshot.id],
            'sandbox_id': new_sandbox_id,
            'parent_snapshot_id': snapshot_id_map.get(old_snapshot.parent_snapshot_id)
        })
        await snapshot_store.save(new_snapshot)
    
    new_head_id = snapshot_id_map.get(archive.sandbox.head_snapshot_id)
    new_sandbox = archive.sandbox.model_copy(update={
        'id': new_sandbox_id,
        'head_snapshot_id': new_head_id,
        'name': f"{archive.sandbox.name} (Imported)",
        'created_at': datetime.now(timezone.utc),
        'icon_updated_at': None
    })

    if new_sandbox.id in sandbox_store:
         raise HTTPException(status_code=409, detail=f"A sandbox with the newly generated ID '{new_sandbox.id}' already exists. This is highly unlikely, please try again.")
    
    await sandbox_store.save(new_sandbox)

    logger.info(f"Successfully imported sandbox from JSON, new ID is '{new_sandbox.id}'. Original ID was '{old_sandbox_id}'.")
    return new_sandbox


# PNG 导入/导出端点
@router.get("/{sandbox_id}/export", response_class=Response, summary="Export a Sandbox as PNG")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    # 添加 await 调用异步方法
    snapshots = await snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    
    # 准备导出的沙盒数据，兼容旧版
    export_sandbox_data = sandbox.model_dump()
    export_sandbox_data['graph_collection'] = sandbox.lore.get('graphs', {})

    # 注意：这里传递的是字典，而不是Pydantic模型，因为model_dump已经处理过了
    data_files: Dict[str, Any] = {"sandbox.json": export_sandbox_data}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap.model_dump()

    base_image_bytes = None
    icon_path = persistence_service.get_sandbox_icon_path(str(sandbox.id))
    if icon_path and icon_path.is_file():
        # 读取图标文件是I/O操作
        async with aiofiles.open(icon_path, 'rb') as f:
            base_image_bytes = await f.read()
    
    if not base_image_bytes:
        default_icon_path = persistence_service.get_default_icon_path()
        if default_icon_path.is_file():
             async with aiofiles.open(default_icon_path, 'rb') as f:
                base_image_bytes = await f.read()

    try:
        # 添加 await 调用异步方法
        png_bytes = await persistence_service.export_package(manifest, data_files, base_image_bytes)
    except Exception as e:
        logger.error(f"Failed to create package for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.png"
    return Response(content=png_bytes, media_type="image/png", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post(":import", response_model=Sandbox, summary="Import a Sandbox from PNG")
async def import_sandbox(
    file: UploadFile = File(...),
    sandbox_store: PersistentSandboxStore = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
) -> Sandbox:
    if not file.filename or not file.filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .png file.")

    package_bytes = await file.read()
    
    try:
        # 添加 await 调用异步方法
        manifest, data_files, png_bytes = await persistence_service.import_package(package_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid package: {e}")

    if manifest.package_type != PackageType.SANDBOX_ARCHIVE:
        raise HTTPException(status_code=400, detail=f"Invalid package type. Expected '{PackageType.SANDBOX_ARCHIVE.value}'.")

    try:
        sandbox_data_str = data_files.get(manifest.entry_point)
        if not sandbox_data_str:
            raise ValueError(f"Entry point file '{manifest.entry_point}' not found in package.")
        
        old_sandbox_data = json.loads(sandbox_data_str)
        
        initial_lore = {"graphs": old_sandbox_data.get("graph_collection", {})}
        initial_moment = {}
        definition = {"initial_lore": initial_lore, "initial_moment": initial_moment}
        
        new_id = uuid.uuid4()
        new_sandbox = Sandbox(
            id=new_id,
            name=old_sandbox_data.get('name', 'Imported Sandbox'),
            definition=definition,
            lore=initial_lore,
            created_at=datetime.now(timezone.utc)
        )
        
        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with the newly generated ID '{new_sandbox.id}' already exists.")

        recovered_snapshots = []
        old_to_new_snap_id = {}
        for filename in data_files:
            if filename.startswith("snapshots/"):
                old_id_str = filename.split('/')[1].split('.')[0]
                old_to_new_snap_id[UUID(old_id_str)] = uuid.uuid4()

        for filename, content_str in data_files.items():
            if filename.startswith("snapshots/"):
                old_snapshot_data = json.loads(content_str)
                old_id = UUID(old_snapshot_data.get('id'))
                old_parent_id = old_snapshot_data.get('parent_snapshot_id')
                old_parent_id_uuid = UUID(old_parent_id) if old_parent_id else None
                new_parent_id = old_to_new_snap_id.get(old_parent_id_uuid) if old_parent_id_uuid else None
                
                new_snapshot = StateSnapshot(
                    id=old_to_new_snap_id[old_id],
                    sandbox_id=new_sandbox.id,
                    moment=old_snapshot_data.get('moment', {}),
                    parent_snapshot_id=new_parent_id,
                    triggering_input=old_snapshot_data.get('triggering_input', {}),
                    run_output=old_snapshot_data.get('run_output'),
                    created_at=datetime.fromisoformat(old_snapshot_data.get('created_at')) if old_snapshot_data.get('created_at') else datetime.now(timezone.utc)
                )
                recovered_snapshots.append(new_snapshot)
        
        if not recovered_snapshots:
            raise ValueError("No snapshots found in the package.")

        for snapshot in recovered_snapshots:
            await snapshot_store.save(snapshot)
        
        old_head_id = old_sandbox_data.get('head_snapshot_id')
        if old_head_id:
            new_sandbox.head_snapshot_id = old_to_new_snap_id.get(UUID(old_head_id))

        try:
            # 添加 await 调用异步方法
            await persistence_service.save_sandbox_icon(str(new_sandbox.id), png_bytes)
            new_sandbox.icon_updated_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to set icon for newly imported sandbox {new_sandbox.id}: {e}")

        await sandbox_store.save(new_sandbox)
        
        logger.info(f"Successfully imported sandbox '{new_sandbox.name}' ({new_sandbox.id}) from PNG.")
        return new_sandbox
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to process package data for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {str(e)}")