# plugins/core_codex/api.py (MODIFIED)
import logging
from uuid import UUID
from typing import Dict, Any, List, Literal # <--- 导入 Literal

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

# --- 导入核心依赖 ---
from backend.core.dependencies import Service
from plugins.core_engine.contracts import (
    Sandbox,
    SnapshotStoreInterface,
    EditorUtilsServiceInterface # 导入 core_engine 提供的服务接口
)

# --- 导入本插件的模型 ---
from .models import Codex, CodexEntry

logger = logging.getLogger(__name__)

# 【修改点 1】定义一个扩展的 Scope 类型，专供 Codex API 使用
CodexScope = Literal["lore", "moment", "initial_lore", "initial_moment"]

codex_router = APIRouter(
    prefix="/api/sandboxes/{sandbox_id}/{scope}/codices",
    tags=["Editor API - Codex"]
)

# --- 辅助函数：获取沙盒 (与 core_engine 中的一样) ---
def get_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store"))
) -> Sandbox:
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail=f"Sandbox with ID '{sandbox_id}' not found.")
    return sandbox

# --- 辅助函数：获取目标作用域的字典引用 (新) ---
def _get_target_scope_dict(sandbox: Sandbox, scope: CodexScope) -> Dict[str, Any]:
    """根据 scope 字符串，返回 sandbox 中对应字典的引用。"""
    if scope == "lore":
        return sandbox.lore
    # `definition` 作用域下的两个子域
    elif scope == "initial_lore":
        return sandbox.definition.setdefault("initial_lore", {})
    elif scope == "initial_moment":
        return sandbox.definition.setdefault("initial_moment", {})
    # `moment` 的情况比较特殊，由 perform_live_moment_update 处理，这里不返回
    raise ValueError(f"Cannot get a direct dictionary reference for scope '{scope}'")


# --- 知识库级别 (Codex-Level) API ---

@codex_router.put(
    "/{codex_name}",
    response_model=Sandbox,
    summary="Create or update a codex"
)
async def upsert_codex(
    scope: CodexScope,
    codex_name: str,
    codex_def: Codex,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """创建或完整替换一个知识库的定义。"""
    def update_logic(target_dict: Dict[str, Any]):
        codices = target_dict.setdefault("codices", {})
        codices[codex_name] = codex_def.model_dump(exclude_none=True)
        return target_dict

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        # 复用 "直接更新" 逻辑
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox

@codex_router.delete(
    "/{codex_name}",
    response_model=Sandbox,
    summary="Delete a codex"
)
async def delete_codex(
    scope: CodexScope,
    codex_name: str,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """从指定的作用域中删除一个知识库。"""
    def update_logic(target_dict: Dict[str, Any]):
        codices = target_dict.get("codices")
        if not codices or codex_name not in codices:
             raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found in scope '{scope}'.")
        del codices[codex_name]
        return target_dict

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox

# --- 条目级别 (Entry-Level) API ---

class EntryOrderRequest(BaseModel):
    entry_ids: List[str]


@codex_router.post(
    "/{codex_name}/entries",
    response_model=Sandbox,
    summary="Add a new entry to a codex"
)
async def add_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry: CodexEntry,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """在知识库的条目列表末尾添加一个新条目。如果知识库不存在，会自动创建。"""
    def update_logic(target_dict: Dict[str, Any]):
        codices_dict = target_dict.setdefault("codices", {})
        target_codex = codices_dict.setdefault(codex_name, {"entries": []}) # 确保 codex 和 entries 列表存在
        entries_list = target_codex.setdefault("entries", [])
        
        existing_ids = {e['id'] for e in entries_list if 'id' in e}
        if entry.id in existing_ids:
            raise HTTPException(status_code=409, detail=f"Entry with ID '{entry.id}' already exists in codex '{codex_name}'.")

        entries_list.append(entry.model_dump())
        return target_dict
        
    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox

@codex_router.post(
    "/{codex_name}/entries:reorder",
    response_model=Sandbox,
    summary="Reorder all entries in a codex using an action endpoint"
)
async def reorder_codex_entries(
    scope: CodexScope,
    codex_name: str,
    order_request: EntryOrderRequest,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """通过一个专门的动作端点来重排序知识库中的所有条目。"""
    def update_logic(target_dict: Dict[str, Any]):
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex:
            raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found.")
        
        entries = codex.get("entries", [])
        entry_map = {e['id']: e for e in entries if 'id' in e}
        
        if set(entry_map.keys()) != set(order_request.entry_ids):
             raise HTTPException(
                 status_code=400, 
                 detail="Provided entry IDs do not match the existing set of entries."
             )
             
        codex['entries'] = [entry_map[eid] for eid in order_request.entry_ids]
        return target_dict

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox

@codex_router.put(
    "/{codex_name}/entries/{entry_id}",
    response_model=Sandbox,
    summary="Update an existing entry"
)
async def update_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry_id: str,
    entry_data: CodexEntry,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """更新一个已存在的条目。"""
    if entry_id != entry_data.id:
        raise HTTPException(status_code=400, detail="Entry ID in path does not match entry ID in body.")

    def update_logic(target_dict: Dict[str, Any]):
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex: raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found.")
        
        entries = codex.get("entries", [])
        for i, e in enumerate(entries):
            if e.get('id') == entry_id:
                entries[i] = entry_data.model_dump()
                return target_dict
        raise HTTPException(status_code=404, detail=f"Entry with ID '{entry_id}' not found.")

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox

@codex_router.patch(
    "/{codex_name}/entries/{entry_id}",
    response_model=Sandbox,
    summary="Partially modify an entry"
)
async def patch_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry_id: str,
    patch_data: Dict[str, Any],
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """局部更新一个条目（例如切换 is_enabled）。"""
    def update_logic(target_dict: Dict[str, Any]):
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex: raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found.")
        
        entries = codex.get("entries", [])
        for i, e in enumerate(entries):
            if e.get('id') == entry_id:
                # 检查ID是否在patch数据中，如果是，则不允许修改
                if 'id' in patch_data and patch_data['id'] != entry_id:
                    raise HTTPException(status_code=400, detail="Cannot change entry ID via PATCH.")
                entries[i].update(patch_data)
                # 可选：使用 Pydantic 模型重新验证，确保 patch 后的数据结构仍然有效
                CodexEntry.model_validate(entries[i])
                return target_dict
        raise HTTPException(status_code=404, detail=f"Entry with ID '{entry_id}' not found.")

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox

@codex_router.delete(
    "/{codex_name}/entries/{entry_id}",
    response_model=Sandbox,
    summary="Delete an entry from a codex"
)
async def delete_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry_id: str,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """从知识库中删除一个条目。"""
    def update_logic(target_dict: Dict[str, Any]):
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex:
            raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found.")
        
        entries = codex.get("entries", [])
        entry_to_remove_idx = next((i for i, e in enumerate(entries) if e.get("id") == entry_id), None)

        if entry_to_remove_idx is None:
            raise HTTPException(status_code=404, detail=f"Entry with ID '{entry_id}' not found in codex '{codex_name}'.")

        del entries[entry_to_remove_idx]
        return target_dict

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        return sandbox