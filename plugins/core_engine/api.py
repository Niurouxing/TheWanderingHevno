# plugins/core_engine/api.py

import io
import logging
import json
import uuid  # <-- [新] 导入 uuid 模块
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError, field_validator
from datetime import datetime, timezone
from PIL import Image

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response, FileResponse, JSONResponse  # <-- [新] 导入 JSONResponse

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

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sandboxes", 
    tags=["Sandboxes"]
)

# --- Request/Response Models ---

# ... (现有的 CreateSandboxRequest, SandboxListItem, UpdateSandboxRequest 模型保持不变) ...

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

# --- [新] 用于 JSON 导入/导出的数据模型 ---
class SandboxArchiveJSON(BaseModel):
    """一个自包含的沙盒归档，用于纯JSON格式的导入和导出。"""
    sandbox: Sandbox
    snapshots: List[StateSnapshot]
# --- 结束新模型定义 ---


# --- Sandbox Lifecycle API ---
# ... (现有的 create_sandbox, execute_sandbox_step, revert_sandbox_to_snapshot 保持不变) ...
@router.post("", response_model=Sandbox, status_code=201, summary="Create a new Sandbox")
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
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
    snapshot_store.save(genesis_snapshot)
    
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    
    logger.info(f"Created new sandbox '{sandbox.name}' ({sandbox.id}) using provided definition.")
    return sandbox

@router.post("/{sandbox_id}/step", response_model=Sandbox, summary="Execute a step")
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    engine: ExecutionEngineInterface = Depends(Service("execution_engine"))
):
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
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    target_snapshot = snapshot_store.get(snapshot_id)
    if not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Target snapshot not found or does not belong to this sandbox.")
    
    sandbox.head_snapshot_id = snapshot_id
    
    logger.info(f"Reverted sandbox '{sandbox.name}' ({sandbox.id}) to snapshot {snapshot_id}.")
    return {"message": f"Sandbox '{sandbox.name}' successfully reverted to snapshot {snapshot_id}"}


# --- 其他端点 ---
# ... (现有的 get_sandbox_history, update_sandbox_details, delete_sandbox, list_sandboxes 等保持不变) ...
@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot], summary="Get history")
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store"))
):
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return snapshot_store.find_by_sandbox(sandbox_id)

@router.patch("/{sandbox_id}", response_model=Sandbox, summary="Update Sandbox Details")
async def update_sandbox_details(
    sandbox_id: UUID,
    request_body: UpdateSandboxRequest,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    sandbox.name = request_body.name
    logger.info(f"Updated name for sandbox '{sandbox.id}' to '{sandbox.name}'.")
    return sandbox

@router.delete("/{sandbox_id}", status_code=204, summary="Delete a Sandbox")
async def delete_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
):
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    
    del sandbox_store[sandbox_id]
    logger.info(f"Deleted sandbox '{sandbox_id}' and all associated data.")
    return Response(status_code=204)

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

    persistence_service.save_sandbox_icon(str(sandbox.id), icon_bytes)
    sandbox.icon_updated_at = datetime.now(timezone.utc)
    
    return {"message": "Icon updated successfully."}


@router.get(
    "/{sandbox_id}/export/json", 
    response_class=JSONResponse, 
    summary="Export a Sandbox as JSON"
)
async def export_sandbox_json(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    """
    将单个沙盒及其所有历史快照导出为一个自包含的 JSON 文件。
    """
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    # 使用我们定义的新模型构建归档对象
    archive = SandboxArchiveJSON(sandbox=sandbox, snapshots=snapshots)

    # 准备文件名和响应头
    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.json"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    
    # 使用 JSONResponse 返回，可以设置自定义头
    # model_dump(mode='json') 会将 UUID 和 datetime 等对象正确序列化为 JSON 兼容的字符串
    return JSONResponse(content=archive.model_dump(mode="json"), headers=headers)


@router.post(
    "/import/json", 
    response_model=Sandbox, 
    status_code=201, 
    summary="Import a Sandbox from JSON"
)
async def import_sandbox_json(
    file: UploadFile = File(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
) -> Sandbox:
    """
    从一个 JSON 文件导入一个完整的沙盒。
    为避免冲突，将为导入的沙盒及其所有快照生成新的 UUID。
    """
    if not file.content_type == "application/json":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .json file.")

    try:
        content = await file.read()
        data = json.loads(content)
        archive = SandboxArchiveJSON.model_validate(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON file.")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid sandbox archive format: {e}")

    # --- 核心逻辑：重新映射所有ID以避免冲突 ---
    # 1. 为沙盒和每个快照生成新的ID
    old_sandbox_id = archive.sandbox.id
    new_sandbox_id = uuid.uuid4()
    snapshot_id_map = {snap.id: uuid.uuid4() for snap in archive.snapshots}
    
    # 2. 存储并应用新的快照
    for old_snapshot in archive.snapshots:
        new_snapshot = old_snapshot.model_copy(update={
            'id': snapshot_id_map[old_snapshot.id],
            'sandbox_id': new_sandbox_id,
            'parent_snapshot_id': snapshot_id_map.get(old_snapshot.parent_snapshot_id)
        })
        snapshot_store.save(new_snapshot)
    
    # 3. 创建并存储新的沙盒对象
    new_head_id = snapshot_id_map.get(archive.sandbox.head_snapshot_id)
    new_sandbox = archive.sandbox.model_copy(update={
        'id': new_sandbox_id,
        'head_snapshot_id': new_head_id,
        'name': f"{archive.sandbox.name} (Imported)",
        'created_at': datetime.now(timezone.utc),
        'icon_updated_at': None # 导入的JSON不包含图标信息
    })

    if new_sandbox.id in sandbox_store:
         raise HTTPException(status_code=409, detail=f"A sandbox with the newly generated ID '{new_sandbox.id}' already exists. This is highly unlikely, please try again.")
    
    sandbox_store[new_sandbox.id] = new_sandbox

    logger.info(f"Successfully imported sandbox from JSON, new ID is '{new_sandbox.id}'. Original ID was '{old_sandbox_id}'.")
    return new_sandbox



@router.get("/{sandbox_id}/export", response_class=Response, summary="Export a Sandbox as PNG")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    
    export_sandbox_data = sandbox.model_dump()
    export_sandbox_data['graph_collection'] = sandbox.lore.get('graphs', {})

    data_files: Dict[str, BaseModel] = {"sandbox.json": Sandbox.model_construct(**export_sandbox_data)}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap

    base_image_bytes = None
    icon_path = persistence_service.get_sandbox_icon_path(str(sandbox.id))
    if not icon_path:
        icon_path = persistence_service.get_default_icon_path()
    
    if icon_path.is_file():
        base_image_bytes = icon_path.read_bytes()

    try:
        png_bytes = persistence_service.export_package(manifest, data_files, base_image_bytes)
    except Exception as e:
        logger.error(f"Failed to create package for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox_id}.png"
    return Response(content=png_bytes, media_type="image/png", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post(":import", response_model=Sandbox, summary="Import a Sandbox from PNG")
async def import_sandbox(
    file: UploadFile = File(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store")),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    persistence_service: PersistenceServiceInterface = Depends(Service("persistence_service"))
) -> Sandbox:
    """
    通过一个专门的动作端点从 PNG 文件导入沙盒。
    """
    if not file.filename or not file.filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .png file.")

    package_bytes = await file.read()
    
    try:
        manifest, data_files, png_bytes = persistence_service.import_package(package_bytes)
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
        
        new_sandbox = Sandbox(
            id=old_sandbox_data.get('id', str(uuid.uuid4())),
            name=old_sandbox_data.get('name', 'Imported Sandbox'),
            head_snapshot_id=old_sandbox_data.get('head_snapshot_id'),
            created_at=old_sandbox_data.get('created_at', datetime.now(timezone.utc).isoformat()),
            definition=definition,
            lore=initial_lore
        )
        
        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with ID '{new_sandbox.id}' already exists.")

        recovered_snapshots = []
        for filename, content_str in data_files.items():
            if filename.startswith("snapshots/"):
                old_snapshot_data = json.loads(content_str)
                new_snapshot = StateSnapshot(
                    id=old_snapshot_data.get('id'),
                    sandbox_id=new_sandbox.id,
                    moment=old_snapshot_data.get('world_state', {}),
                    parent_snapshot_id=old_snapshot_data.get('parent_snapshot_id'),
                    triggering_input=old_snapshot_data.get('triggering_input', {}),
                    run_output=old_snapshot_data.get('run_output'),
                    created_at=old_snapshot_data.get('created_at', datetime.now(timezone.utc).isoformat())
                )
                recovered_snapshots.append(new_snapshot)
        
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
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to process package data for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {str(e)}")