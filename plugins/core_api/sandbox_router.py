# plugins/core_api/sandbox_router.py

import io
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

# 从平台核心契约导入数据模型和接口
from backend.core.contracts import (
    Sandbox, 
    StateSnapshot, 
    GraphCollection,
    ExecutionEngineInterface,
    SnapshotStoreInterface
)

# 从本插件的依赖注入文件中导入 "getters"
from .dependencies import get_sandbox_store, get_snapshot_store, get_engine

# 【关键】从依赖插件 core_persistence 导入其服务和模型
from plugins.core_persistence.service import PersistenceService
from plugins.core_persistence.models import PackageManifest, PackageType
from plugins.core_persistence.dependencies import get_persistence_service

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

# --- Sandbox Lifecycle API ---

@router.post("", response_model=Sandbox, status_code=201, summary="Create a new Sandbox")
async def create_sandbox(
    request_body: CreateSandboxRequest, 
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
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

@router.post("/{sandbox_id}/step", response_model=StateSnapshot, summary="Execute a step")
async def execute_sandbox_step(
    sandbox_id: UUID, 
    user_input: Dict[str, Any] = Body(...),
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    engine: ExecutionEngineInterface = Depends(get_engine)
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
    
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    
    return new_snapshot

@router.get("/{sandbox_id}/history", response_model=List[StateSnapshot], summary="Get history")
async def get_sandbox_history(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
):
    """获取一个沙盒的所有历史快照，按时间顺序排列。"""
    if sandbox_id not in sandbox_store:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
        
    # 如果存在，则继续执行原逻辑
    return snapshot_store.find_by_sandbox(sandbox_id)

@router.put("/{sandbox_id}/revert", status_code=200, summary="Revert to a snapshot")
async def revert_sandbox_to_snapshot(
    sandbox_id: UUID, 
    snapshot_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store)
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

@router.get("/{sandbox_id}/export", response_class=StreamingResponse, summary="Export a Sandbox")
async def export_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    persistence_service: PersistenceService = Depends(get_persistence_service)
):
    """将一个沙盒及其完整历史导出为一个 .hevno.zip 包文件。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots:
        raise HTTPException(status_code=404, detail="No snapshots found for this sandbox to export.")

    # 1. 准备清单和数据文件
    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name}
    )
    data_files: Dict[str, BaseModel] = {"sandbox.json": sandbox}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap

    # 2. 调用 persistence_service 进行打包
    try:
        zip_bytes = persistence_service.export_package(manifest, data_files)
    except Exception as e:
        logger.error(f"Failed to create package for sandbox {sandbox_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create package: {e}")

    # 3. 返回文件流
    filename = f"hevno_sandbox_{sandbox.name.replace(' ', '_')}_{sandbox.id}.hevno.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/import", response_model=Sandbox, summary="Import a Sandbox")
async def import_sandbox(
    file: UploadFile = File(..., description="A .hevno.zip package file."),
    sandbox_store: Dict[UUID, Sandbox] = Depends(get_sandbox_store),
    snapshot_store: SnapshotStoreInterface = Depends(get_snapshot_store),
    persistence_service: PersistenceService = Depends(get_persistence_service)
) -> Sandbox:
    """从一个 .hevno.zip 文件导入一个沙盒及其完整历史。"""
    if not file.filename or not file.filename.endswith(".hevno.zip"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .hevno.zip file.")

    zip_bytes = await file.read()
    
    # 1. 调用 persistence_service 解包
    try:
        manifest, data_files = persistence_service.import_package(zip_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid package: {e}")

    if manifest.package_type != PackageType.SANDBOX_ARCHIVE:
        raise HTTPException(status_code=400, detail=f"Invalid package type. Expected '{PackageType.SANDBOX_ARCHIVE.value}'.")
    
    # 【未来扩展】在这里可以检查 manifest.required_plugins

    # 2. 处理解包后的数据
    try:
        sandbox_data_str = data_files.get(manifest.entry_point)
        if not sandbox_data_str:
            raise ValueError(f"Entry point file '{manifest.entry_point}' not found in package.")
        
        # 恢复沙盒对象
        new_sandbox = Sandbox.model_validate_json(sandbox_data_str)
        if new_sandbox.id in sandbox_store:
            raise HTTPException(status_code=409, detail=f"Conflict: A sandbox with ID '{new_sandbox.id}' already exists.")

        # 恢复所有快照对象
        recovered_snapshots = []
        for filename, content_str in data_files.items():
            if filename.startswith("snapshots/"):
                snapshot = StateSnapshot.model_validate_json(content_str)
                if snapshot.sandbox_id != new_sandbox.id:
                    raise ValueError(f"Snapshot {snapshot.id} does not belong to the imported sandbox {new_sandbox.id}.")
                recovered_snapshots.append(snapshot)
        
        if not recovered_snapshots:
            raise ValueError("No snapshots found in the package.")

        # 3. 如果所有数据都有效，则原子性地保存到存储中
        for snapshot in recovered_snapshots:
            snapshot_store.save(snapshot)
        sandbox_store[new_sandbox.id] = new_sandbox
        
        logger.info(f"Successfully imported sandbox '{new_sandbox.name}' ({new_sandbox.id}).")
        return new_sandbox

    except (ValidationError, ValueError) as e:
        logger.warning(f"Failed to process package data for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process package data: {str(e)}")