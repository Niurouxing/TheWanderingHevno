# plugins/core_engine/editor_api.py
import logging
from uuid import UUID
from typing import Dict, Any, List, Literal

import jsonpatch
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Body, Response, status

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

editor_router = APIRouter(
    prefix="/api/sandboxes/{sandbox_id}",
    tags=["Editor API - Graphs & Scopes"],
)

Scope = Literal["definition", "lore", "moment"]

# --- 辅助函数 (保持不变) ---
def get_sandbox(
    sandbox_id: UUID,
    sandbox_store: Dict[UUID, Sandbox] = Depends(Service("sandbox_store"))
) -> Sandbox:
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail=f"Sandbox with ID '{sandbox_id}' not found.")
    return sandbox

def get_scope_content_data(
    scope: Scope,
    sandbox: Sandbox,
    snapshot_store: SnapshotStoreInterface
) -> Dict[str, Any]:
    if scope == "definition":
        return sandbox.definition
    if scope == "lore":
        return sandbox.lore
    if scope == "moment":
        if not sandbox.head_snapshot_id:
            return {}
        # get() is sync from cache
        head_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot:
            # This case might require an async find if the cache can be cold
            raise HTTPException(status_code=404, detail=f"Head snapshot for sandbox '{sandbox.id}' not found.")
        return head_snapshot.moment
    raise HTTPException(status_code=400, detail=f"Invalid scope '{scope}'")

# --- 作用域 API (返回Sandbox是可接受的) ---
@editor_router.get("/{scope}", response_model=Dict[str, Any], summary="Get the full content of a scope")
async def get_scope_content(
    scope: Scope, sandbox: Sandbox = Depends(get_sandbox),
    snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    # This might need to become async if get() needs to hit disk
    return get_scope_content_data(scope, sandbox, snapshot_store)

@editor_router.put(
    "/{scope}", 
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Completely replace the content of a scope"
)
async def replace_scope_content(
    scope: Scope, data: Dict[str, Any] = Body(...),
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service")),
):
    if scope == "definition":
        def update_definition(s: Sandbox): s.definition = data
        await editor_utils.perform_sandbox_update(sandbox, update_definition)
    elif scope == "lore":
        def update_lore(s: Sandbox): s.lore = data
        await editor_utils.perform_sandbox_update(sandbox, update_lore)
    elif scope == "moment":
        def replace_moment(m: Dict[str, Any]) -> Dict[str, Any]: return data
        await editor_utils.perform_live_moment_update(sandbox, replace_moment)
    
    # 2. 修改返回值
    return None
@editor_router.patch(
    "/{scope}", 
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Partially modify a scope using JSON-Patch"
)
async def patch_scope_content(
    scope: Scope, patch: List[Dict[str, Any]] = Body(...),
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service")),
):
    try:
        if scope == "definition":
            def patch_definition(s: Sandbox): jsonpatch.apply_patch(s.definition, patch, in_place=True)
            await editor_utils.perform_sandbox_update(sandbox, patch_definition)
        elif scope == "lore":
            def patch_lore(s: Sandbox): jsonpatch.apply_patch(s.lore, patch, in_place=True)
            await editor_utils.perform_sandbox_update(sandbox, patch_lore)
        elif scope == "moment":
            def apply_patch_to_moment(m: Dict[str, Any]) -> Dict[str, Any]:
                jsonpatch.apply_patch(m, patch, in_place=True)
                return m
            await editor_utils.perform_live_moment_update(sandbox, apply_patch_to_moment)
        
        # 2. 修改返回值
        return None

    except jsonpatch.JsonPatchException as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON-Patch operation: {e}")
    except Exception as e:
        logger.error(f"Error applying patch to scope '{scope}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- 图 (Graph) API (已遵循良好实践) ---
@editor_router.get("/{scope}/graphs", response_model=Dict[str, Any], summary="Get all graphs within a scope")
async def list_graphs(
    scope: Scope, sandbox: Sandbox = Depends(get_sandbox), snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    scope_data = get_scope_content_data(scope, sandbox, snapshot_store)
    return scope_data.get("graphs", {})

@editor_router.get("/{scope}/graphs/{graph_name}", response_model=GraphDefinition, summary="Get a single graph by name")
async def get_graph(
    scope: Scope, graph_name: str,
    sandbox: Sandbox = Depends(get_sandbox), snapshot_store: SnapshotStoreInterface = Depends(Service("snapshot_store")),
):
    scope_data = get_scope_content_data(scope, sandbox, snapshot_store)
    graphs = scope_data.get("graphs", {})
    graph_def = graphs.get(graph_name)
    if graph_def is None:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found in scope '{scope}'.")
    return graph_def

@editor_router.put("/{scope}/graphs/{graph_name}", response_model=GraphDefinition, summary="Create or update a graph")
async def upsert_graph(
    scope: Scope, graph_name: str, graph_def: GraphDefinition,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        graphs = s_scope.setdefault("graphs", {})
        
        # --- 核心修改 ---
        # 1. 将传入的 Pydantic 模型转换为字典
        graph_data_to_save = graph_def.model_dump(exclude_unset=True)
        # 2. 在这个字典中注入类型标记
        graph_data_to_save["__hevno_type__"] = "hevno/graph"
        # 3. 将带有标记的字典存入
        graphs[graph_name] = graph_data_to_save
        
        return s_scope
    
    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        # 这个包装器逻辑是正确的，因为它确保了对沙盒对象的修改能够被正确应用
        def sandbox_update_wrapper(s: Sandbox):
            # 获取正确的子作用域字典 (lore 或 definition)
            target_scope = getattr(s, scope)
            update_logic(target_scope)
        await editor_utils.perform_sandbox_update(sandbox, sandbox_update_wrapper)
        
    return graph_def

@editor_router.delete("/{scope}/graphs/{graph_name}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Delete a graph")
async def delete_graph(
    scope: Scope, graph_name: str,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        graphs = s_scope.get("graphs", {})
        if graph_name not in graphs:
            raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found in scope '{scope}'.")
        del graphs[graph_name]
        return s_scope

    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return None

# --- 节点 (Node) API (已遵循良好实践) ---
class NodeOrderRequest(BaseModel): node_ids: List[str]

@editor_router.post("/{scope}/graphs/{graph_name}/nodes", response_model=GenericNode, status_code=status.HTTP_201_CREATED, summary="Add a new node to a graph")
async def add_node(
    scope: Scope, graph_name: str, node: GenericNode,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        graph = s_scope.get("graphs", {}).get(graph_name)
        if not graph: raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found.")
        nodes = graph.setdefault("nodes", [])
        if any(n.get('id') == node.id for n in nodes):
            raise HTTPException(status_code=409, detail=f"Node with ID '{node.id}' already exists.")
        nodes.append(node.model_dump(exclude_unset=True))
        return s_scope

    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return node

@editor_router.put("/{scope}/graphs/{graph_name}/nodes/{node_id}", response_model=GenericNode, summary="Update an existing node")
async def update_node(
    scope: Scope, graph_name: str, node_id: str, node_data: GenericNode,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    if node_id != node_data.id: raise HTTPException(status_code=400, detail="Node ID mismatch.")

    def update_logic(s_scope: Dict[str, Any]):
        graph = s_scope.get("graphs", {}).get(graph_name)
        if not graph: raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found.")
        nodes = graph.get("nodes", [])
        for i, n in enumerate(nodes):
            if n.get('id') == node_id:
                nodes[i] = node_data.model_dump(exclude_unset=True)
                return s_scope
        raise HTTPException(status_code=404, detail=f"Node with ID '{node_id}' not found.")

    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return node_data

@editor_router.delete("/{scope}/graphs/{graph_name}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Delete a node from a graph")
async def delete_node(
    scope: Scope, graph_name: str, node_id: str,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        graph = s_scope.get("graphs", {}).get(graph_name)
        if not graph: raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found.")
        nodes = graph.get("nodes", [])
        node_to_remove_idx = next((i for i, n in enumerate(nodes) if n.get('id') == node_id), None)
        if node_to_remove_idx is None: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        del nodes[node_to_remove_idx]
        return s_scope
        
    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return None

# --- 指令 (Instruction) API (已遵循良好实践) ---

@editor_router.post("/{scope}/graphs/{graph_name}/nodes/{node_id}/runtimes", response_model=RuntimeInstruction, status_code=status.HTTP_201_CREATED, summary="Add an instruction to a node")
async def add_instruction(
    scope: Scope, graph_name: str, node_id: str, instruction: RuntimeInstruction,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs", {}).get(graph_name, {}).get("nodes", []) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        node.setdefault("run", []).append(instruction.model_dump(exclude_unset=True))
        return s_scope

    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return instruction

@editor_router.put("/{scope}/graphs/{graph_name}/nodes/{node_id}/runtimes/{runtime_index}", response_model=RuntimeInstruction, summary="Update a specific instruction")
async def update_instruction(
    scope: Scope, graph_name: str, node_id: str, runtime_index: int, instruction: RuntimeInstruction,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs", {}).get(graph_name, {}).get("nodes", []) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        runtimes = node.get("run", [])
        if not 0 <= runtime_index < len(runtimes): raise HTTPException(status_code=404, detail=f"Runtime index {runtime_index} out of bounds.")
        runtimes[runtime_index] = instruction.model_dump(exclude_unset=True)
        return s_scope
        
    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return instruction

@editor_router.delete("/{scope}/graphs/{graph_name}/nodes/{node_id}/runtimes/{runtime_index}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Delete a specific instruction")
async def delete_instruction(
    scope: Scope, graph_name: str, node_id: str, runtime_index: int,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    def update_logic(s_scope: Dict[str, Any]):
        node = next((n for n in s_scope.get("graphs", {}).get(graph_name, {}).get("nodes", []) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        runtimes = node.get("run", [])
        if not 0 <= runtime_index < len(runtimes): raise HTTPException(status_code=404, detail=f"Runtime index {runtime_index} out of bounds.")
        del runtimes[runtime_index]
        return s_scope
        
    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return None

# --- 批量操作API (已优化) ---
@editor_router.post(
    "/{scope}/graphs/{graph_name}/nodes:reorder", 
    status_code=status.HTTP_204_NO_CONTENT, # [API OPTIMIZATION]
    response_class=Response, 
    summary="Reorder all nodes in a graph"
)
async def reorder_nodes(
    scope: Scope, graph_name: str, order_request: NodeOrderRequest,
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
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
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    return None

@editor_router.put(
    "/{scope}/graphs/{graph_name}/nodes/{node_id}/run", 
    response_model=GenericNode, # [API OPTIMIZATION]
    summary="Replace all instructions in a node"
)
async def replace_all_instructions(
    scope: Scope, graph_name: str, node_id: str, instructions: List[RuntimeInstruction],
    sandbox: Sandbox = Depends(get_sandbox),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    updated_node_data = None

    def update_logic(s_scope: Dict[str, Any]):
        nonlocal updated_node_data
        graph = s_scope.get("graphs", {}).get(graph_name)
        if not graph: raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found.")
        
        node = next((n for n in graph.get("nodes", []) if n.get("id") == node_id), None)
        if not node: raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
        
        node["run"] = [instr.model_dump(exclude_unset=True) for instr in instructions]
        updated_node_data = node # Capture the updated node data
        return s_scope
        
    if scope == "moment":
        await editor_utils.perform_live_moment_update(sandbox, update_logic)
    else:
        await editor_utils.perform_sandbox_update(sandbox, lambda s: update_logic(getattr(s, scope)))
    
    if updated_node_data is None:
        # This should not happen if the logic above is correct
        raise HTTPException(status_code=500, detail="Failed to retrieve updated node after operation.")
        
    return updated_node_data