# plugins/core_codex/api.py
import logging
from uuid import UUID
from typing import Dict, Any, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Body, Response, status
from pydantic import BaseModel

# --- 核心依赖 ---
from backend.core.dependencies import Service
from plugins.core_engine.contracts import (
    Sandbox,
    EditorUtilsServiceInterface,
    SnapshotStoreInterface # 仍然需要它来解析依赖，即使不直接传给函数
)

# --- 导入本插件的模型 ---
from .models import Codex, CodexEntry

logger = logging.getLogger(__name__)

# CodexScope 现在可以更灵活地指向 definition 中的初始状态
CodexScope = Literal["lore", "moment", "initial_lore", "initial_moment"]

codex_router = APIRouter(
    prefix="/api/sandboxes/{sandbox_id}/{scope}/codices",
    tags=["Editor API - Codex"]
)

# --- 辅助函数 (保持不变) ---
def get_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store"))
) -> Sandbox:
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail=f"Sandbox with ID '{sandbox_id}' not found.")
    return sandbox

def _get_target_scope_dict(sandbox: Sandbox, scope: CodexScope) -> Dict[str, Any]:
    """获取一个可变的字典引用，用于 definition.initial_* 或 lore。"""
    if scope == "lore":
        return sandbox.lore
    elif scope == "initial_lore":
        return sandbox.definition.setdefault("initial_lore", {})
    elif scope == "initial_moment":
        return sandbox.definition.setdefault("initial_moment", {})
    raise ValueError(f"Cannot get a direct dictionary reference for scope '{scope}'")

# --- 知识库级别 (Codex-Level) API ---

@codex_router.put(
    "/{codex_name}",
    response_model=Codex, # 【API 优化】返回被操作的Codex本身
    summary="Create or update a codex and persist changes"
)
async def upsert_codex(
    scope: CodexScope,
    codex_name: str,
    codex_def: Codex,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(target_dict: Dict[str, Any]):
        codices = target_dict.setdefault("codices", {})
        codices[codex_name] = codex_def.model_dump(exclude_unset=True)
        return target_dict

    if scope == "moment":
        # 调用已是异步，且不再需要 snapshot_store 参数
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        # 添加 await 来触发持久化
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
    
    return codex_def

@codex_router.delete(
    "/{codex_name}",
    status_code=status.HTTP_204_NO_CONTENT, # 【API 优化】使用 204 No Content
    response_class=Response,
    summary="Delete a codex and persist changes"
)
async def delete_codex(
    scope: CodexScope,
    codex_name: str,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(target_dict: Dict[str, Any]):
        codices = target_dict.get("codices")
        if not codices or codex_name not in codices:
             raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found in scope '{scope}'.")
        del codices[codex_name]
        return target_dict

    if scope == "moment":
        # 调用已是异步，且不再需要 snapshot_store 参数
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        # 添加 await 来触发持久化
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
    
    return None

# --- 条目级别 (Entry-Level) API ---

class EntryOrderRequest(BaseModel):
    entry_ids: List[str]

@codex_router.post(
    "/{codex_name}/entries",
    response_model=CodexEntry,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new entry to a codex and persist changes"
)
async def add_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry: CodexEntry,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(target_dict: Dict[str, Any]):
        codices_dict = target_dict.setdefault("codices", {})
        target_codex = codices_dict.setdefault(codex_name, {"entries": []})
        entries_list = target_codex.setdefault("entries", [])
        
        if any(e.get('id') == entry.id for e in entries_list):
            raise HTTPException(status_code=409, detail=f"Entry with ID '{entry.id}' already exists in codex '{codex_name}'.")

        entries_list.append(entry.model_dump())
        return target_dict
        
    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))

    return entry


@codex_router.post(
    "/{codex_name}/entries:reorder",
    # 【API优化】返回 204 No Content 表示操作成功但无内容返回，更高效。
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Reorder all entries in a codex and persist changes"
)
async def reorder_codex_entries(
    scope: CodexScope,
    codex_name: str,
    order_request: EntryOrderRequest,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service")),
):
    """
    重新排序指定知识库中的条目。
    此端点在成功后返回 204 No Content，表示操作已应用。
    """
    # 核心的修改逻辑，在字典上就地操作。
    def update_logic(target_dict: Dict[str, Any]):
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex:
            raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found in scope '{scope}'.")
        
        entries = codex.get("entries", [])
        # 使用字典进行快速查找和验证
        entry_map = {e['id']: e for e in entries if 'id' in e}
        
        # 验证传入的ID集合是否与现有ID集合完全匹配
        if set(entry_map.keys()) != set(order_request.entry_ids):
             raise HTTPException(status_code=400, detail="Provided entry IDs do not match the existing set of entries.")
        
        # 根据请求的顺序重新构建条目列表
        codex['entries'] = [entry_map[eid] for eid in order_request.entry_ids]
        return target_dict

    # 根据作用域，调用正确的、异步的、持久化的更新方法
    if scope == "moment":
        # 对 'moment' 的修改会创建新的快照
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        # 对 'lore' 或 'definition' 的修改直接在沙盒对象上进行
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))

    # 【API优化】由于状态码是 204, FastAPI 会自动处理，无需返回任何内容。
    # 返回 None 是最清晰的做法。
    return None
    
@codex_router.put(
    "/{codex_name}/entries/{entry_id}",
    response_model=CodexEntry,
    summary="Update an existing entry and persist changes"
)
async def update_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry_id: str,
    entry_data: CodexEntry,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
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
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        
    return entry_data

@codex_router.patch(
    "/{codex_name}/entries/{entry_id}",
    response_model=CodexEntry,
    summary="Partially modify an entry and persist changes"
)
async def patch_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry_id: str,
    patch_data: Dict[str, Any],
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    updated_entry = None

    def update_logic(target_dict: Dict[str, Any]):
        nonlocal updated_entry
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex: raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found.")
        
        entries = codex.get("entries", [])
        for i, e in enumerate(entries):
            if e.get('id') == entry_id:
                if 'id' in patch_data and patch_data['id'] != entry_id:
                    raise HTTPException(status_code=400, detail="Cannot change entry ID via PATCH.")
                
                e.update(patch_data)
                validated_entry = CodexEntry.model_validate(e)
                entries[i] = validated_entry.model_dump()
                updated_entry = validated_entry
                return target_dict
        raise HTTPException(status_code=404, detail=f"Entry with ID '{entry_id}' not found.")

    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
        
    if updated_entry is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated entry after patch.")
        
    return updated_entry

@codex_router.delete(
    "/{codex_name}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete an entry from a codex and persist changes"
)
async def delete_codex_entry(
    scope: CodexScope,
    codex_name: str,
    entry_id: str,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(target_dict: Dict[str, Any]):
        codex = target_dict.get("codices", {}).get(codex_name)
        if not codex: raise HTTPException(status_code=404, detail=f"Codex '{codex_name}' not found.")
        
        entries = codex.get("entries", [])
        entry_to_remove_idx = next((i for i, e in enumerate(entries) if e.get("id") == entry_id), None)

        if entry_to_remove_idx is None:
            raise HTTPException(status_code=404, detail=f"Entry with ID '{entry_id}' not found in codex '{codex_name}'.")

        del entries[entry_to_remove_idx]
        return target_dict

    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        target_scope_dict = _get_target_scope_dict(sandbox, scope)
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(target_scope_dict))
    
    return None