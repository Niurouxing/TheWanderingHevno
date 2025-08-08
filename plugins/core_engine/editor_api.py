# plugins/core_engine/editor_api.py
import logging
from uuid import UUID
from typing import Dict, Any, List, Literal

import jsonpatch
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Body

from backend.core.dependencies import Service
from plugins.core_engine.contracts import (
    Sandbox,
    StateSnapshot,
    SnapshotStoreInterface,
    GraphDefinition,
    GenericNode,
    RuntimeInstruction,
    EditorUtilsServiceInterface
)

logger = logging.getLogger(__name__)

# 为编辑器创建一个独立的路由器
# 我们将 {sandbox_id} 作为前缀，这样所有端点都能自动获得它。
editor_router = APIRouter(
    prefix="/api/sandboxes/{sandbox_id}",
    tags=["Editor API - Graphs & Scopes"],
)

# 定义一个类型别名来限定 scope 参数
Scope = Literal["definition", "lore", "moment"]

# --- 辅助函数：获取沙盒 ---
def get_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store"))
) -> Sandbox:
    """FastAPI依赖项，用于安全地获取沙盒实例。"""
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail=f"Sandbox with ID '{sandbox_id}' not found.")
    return sandbox

# --- 作用域 API ---
@editor_router.get("/{scope}", response_model=Dict[str, Any], summary="Get the full content of a scope")
async def get_scope_content(
    scope: Scope,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    """获取指定作用域的完整内容。"""
    if scope == "definition":
        return sandbox.definition
    if scope == "lore":
        return sandbox.lore
    if scope == "moment":
        if not sandbox.head_snapshot_id:
            return {}
        head_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot:
            raise HTTPException(status_code=404, detail=f"Head snapshot for sandbox '{sandbox.id}' not found.")
        return head_snapshot.moment

@editor_router.put("/{scope}", response_model=Sandbox, summary="Completely replace the content of a scope")
async def replace_scope_content(
    scope: Scope,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service")),
    data: Dict[str, Any] = Body(...)
):
    """**完整替换**指定作用域的内容。"""
    if scope == "definition":
        def update_definition(s: Sandbox): s.definition = data
        return editor_utils.perform_sandbox_update(sandbox, update_definition)
    if scope == "lore":
        def update_lore(s: Sandbox): s.lore = data
        return editor_utils.perform_sandbox_update(sandbox, update_lore)
    if scope == "moment":
        def replace_moment(m: Dict[str, Any]) -> Dict[str, Any]: return data
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, replace_moment)

@editor_router.patch("/{scope}", response_model=Sandbox, summary="Partially modify a scope using JSON-Patch")
async def patch_scope_content(
    scope: Scope,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service")),
    patch: List[Dict[str, Any]] = Body(...)
):
    """使用 **JSON-Patch (RFC 6902)** 对作用域进行原子性的局部修改。"""
    try:
        if scope == "definition":
            def patch_definition(s: Sandbox): jsonpatch.apply_patch(s.definition, patch, inplace=True)
            return editor_utils.perform_sandbox_update(sandbox, patch_definition)
        if scope == "lore":
            def patch_lore(s: Sandbox): jsonpatch.apply_patch(s.lore, patch, inplace=True)
            return editor_utils.perform_sandbox_update(sandbox, patch_lore)
        if scope == "moment":
            def apply_patch_to_moment(m: Dict[str, Any]) -> Dict[str, Any]:
                jsonpatch.apply_patch(m, patch, inplace=True)
                return m
            return editor_utils.perform_live_moment_update(sandbox, snapshot_store, apply_patch_to_moment)
    except jsonpatch.JsonPatchException as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON-Patch operation: {e}")
    except Exception as e:
        logger.error(f"Error applying patch to scope '{scope}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===============================================
# === 结构化图 (Graphs) API ===
# ===============================================

# --- 图级别 (Graph-Level) API ---
@editor_router.get("/{scope}/graphs", response_model=Dict[str, Any], summary="Get all graphs within a scope")
async def list_graphs(
    scope: Scope,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    """获取指定作用域下的所有图定义。"""
    if scope == "definition": return sandbox.definition.get("graphs", {})
    if scope == "lore": return sandbox.lore.get("graphs", {})
    if scope == "moment":
        if not sandbox.head_snapshot_id: return {}
        head_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot: return {}
        return dict(head_snapshot.moment).get("graphs", {})

@editor_router.put("/{scope}/graphs/{graph_name}", response_model=Sandbox, summary="Create or update a graph")
async def upsert_graph(
    scope: Scope,
    graph_name: str,
    graph_def: GraphDefinition,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """创建或完整替换一个图的定义。"""
    def update_logic(s_scope: Dict[str, Any]):
        graphs = s_scope.setdefault("graphs", {})
        graphs[graph_name] = graph_def.model_dump(exclude_unset=True)
        return s_scope
    
    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox

@editor_router.delete("/{scope}/graphs/{graph_name}", response_model=Sandbox, summary="Delete a graph")
async def delete_graph(
    scope: Scope,
    graph_name: str,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """从指定作用域中删除一个图。"""
    def update_logic(s_scope: Dict[str, Any]):
        graphs = s_scope.get("graphs", {})
        if graph_name in graphs:
            del graphs[graph_name]
        else:
            raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found in scope '{scope}'.")
        return s_scope

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox

# --- 节点级别 (Node-Level) API ---
class NodeOrderRequest(BaseModel):
    node_ids: List[str]

@editor_router.post("/{scope}/graphs/{graph_name}/nodes", response_model=Sandbox, summary="Add a new node to a graph")
async def add_node(
    scope: Scope,
    graph_name: str,
    node: GenericNode,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """在图的节点列表末尾添加一个新节点。"""
    def update_logic(s_scope: Dict[str, Any]):
        graph = s_scope.get("graphs", {}).get(graph_name)
        if not graph:
            raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found.")
        
        nodes = graph.setdefault("nodes", [])
        if any(n.get('id') == node.id for n in nodes):
            raise HTTPException(status_code=409, detail=f"Node with ID '{node.id}' already exists in graph '{graph_name}'.")

        nodes.append(node.model_dump(exclude_unset=True))
        return s_scope

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox

@editor_router.put("/{scope}/graphs/{graph_name}/nodes/{node_id}", response_model=Sandbox, summary="Update an existing node")
async def update_node(
    scope: Scope,
    graph_name: str,
    node_id: str,
    node_data: GenericNode,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """更新一个已存在的节点。"""
    if node_id != node_data.id:
        raise HTTPException(status_code=400, detail="Node ID in path does not match Node ID in body.")

    def update_logic(s_scope: Dict[str, Any]):
        nodes = s_scope.get("graphs", {}).get(graph_name, {}).get("nodes", [])
        for i, n in enumerate(nodes):
            if n.get('id') == node_id:
                nodes[i] = node_data.model_dump(exclude_unset=True)
                return s_scope
        raise HTTPException(status_code=404, detail=f"Node with ID '{node_id}' not found.")

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox
        
@editor_router.delete("/{scope}/graphs/{graph_name}/nodes/{node_id}", response_model=Sandbox, summary="Delete a node from a graph")
async def delete_node(
    scope: Scope,
    graph_name: str,
    node_id: str,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """从图中删除一个节点。"""
    def update_logic(s_scope: Dict[str, Any]):
        nodes = s_scope.get("graphs", {}).get(graph_name, {}).get("nodes", [])
        node_to_remove_idx = next((i for i, n in enumerate(nodes) if n.get('id') == node_id), None)
        if node_to_remove_idx is not None:
            del nodes[node_to_remove_idx]
            return s_scope
        raise HTTPException(status_code=404, detail=f"Node with ID '{node_id}' not found.")
        
    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox

@editor_router.post("/{scope}/graphs/{graph_name}/nodes:reorder", response_model=Sandbox, summary="Reorder all nodes in a graph")
async def reorder_nodes(
    scope: Scope,
    graph_name: str,
    order_request: NodeOrderRequest,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """重排序图中的所有节点。"""
    def update_logic(s_scope: Dict[str, Any]):
        graph = s_scope.get("graphs", {}).get(graph_name)
        if not graph: raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found.")
        
        nodes = graph.get("nodes", [])
        node_map = {n['id']: n for n in nodes}
        
        if set(node_map.keys()) != set(order_request.node_ids):
             raise HTTPException(status_code=400, detail="Provided node IDs do not match the existing set of nodes.")
             
        graph['nodes'] = [node_map[nid] for nid in order_request.node_ids]
        return s_scope

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox
        
# --- 指令级别 (Instruction-Level) API ---
@editor_router.post("/{scope}/graphs/{graph_name}/nodes/{node_id}/runtimes", response_model=Sandbox, summary="Add an instruction to a node")
async def add_instruction(
    scope: Scope,
    graph_name: str,
    node_id: str,
    instruction: RuntimeInstruction,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """在节点的指令列表末尾添加一个新指令。"""
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs",{}).get(graph_name,{}).get("nodes",[]) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        node.setdefault("run", []).append(instruction.model_dump(exclude_unset=True))
        return s_scope

    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox

@editor_router.put("/{scope}/graphs/{graph_name}/nodes/{node_id}/runtimes/{runtime_index}", response_model=Sandbox, summary="Update a specific instruction")
async def update_instruction(
    scope: Scope,
    graph_name: str,
    node_id: str,
    runtime_index: int,
    instruction: RuntimeInstruction,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """更新指定索引的指令。"""
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs",{}).get(graph_name,{}).get("nodes",[]) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        runtimes = node.get("run", [])
        if not 0 <= runtime_index < len(runtimes): raise HTTPException(status_code=404, detail=f"Runtime index {runtime_index} out of bounds.")
        runtimes[runtime_index] = instruction.model_dump(exclude_unset=True)
        return s_scope
        
    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox
        
@editor_router.delete("/{scope}/graphs/{graph_name}/nodes/{node_id}/runtimes/{runtime_index}", response_model=Sandbox, summary="Delete a specific instruction")
async def delete_instruction(
    scope: Scope,
    graph_name: str,
    node_id: str,
    runtime_index: int,
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """删除指定索引的指令。"""
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs",{}).get(graph_name,{}).get("nodes",[]) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        runtimes = node.get("run", [])
        if not 0 <= runtime_index < len(runtimes): raise HTTPException(status_code=404, detail=f"Runtime index {runtime_index} out of bounds.")
        del runtimes[runtime_index]
        return s_scope
        
    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox

@editor_router.put("/{scope}/graphs/{graph_name}/nodes/{node_id}/run", response_model=Sandbox, summary="Replace all instructions in a node")
async def replace_all_instructions(
    scope: Scope,
    graph_name: str,
    node_id: str,
    instructions: List[RuntimeInstruction],
    sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """完整替换一个节点的所有指令，用于重排序或批量修改。"""
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs",{}).get(graph_name,{}).get("nodes",[]) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        node["run"] = [instr.model_dump(exclude_unset=True) for instr in instructions]
        return s_scope
        
    if scope == "moment":
        return editor_utils.perform_live_moment_update(sandbox, snapshot_store, update_logic)
    else:
        editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
        return sandbox