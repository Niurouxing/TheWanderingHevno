import logging
from uuid import UUID

from fastapi import HTTPException, Depends, Body, APIRouter

from backend.core.dependencies import Service
from backend.core.utils import _navigate_to_sub_path, unwrap_dot_accessible_dicts

from .contracts import (
    Sandbox,
    EditorUtilsServiceInterface,
    SnapshotStoreInterface,
    StateSnapshot,
    SandboxStoreInterface,
    Mutation,
    MutateResourceRequest,
    ResourceQueryRequest,
    ResourceQueryResponse,
    MutateResourceResponse,
)

logger = logging.getLogger(__name__)

#  路由器和标签
editor_router = APIRouter(
    prefix="/api/sandboxes/{sandbox_id}",
    tags=["Editor API - Resource Mutation"],
)

# 辅助函数 get_sandbox 保持不变
def get_sandbox(
    sandbox_id: UUID,
    sandbox_store: dict = Depends(Service("sandbox_store"))
) -> Sandbox:
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail=f"Sandbox with ID '{sandbox_id}' not found.")
    return sandbox


# --- 统一资源查询API ---
@editor_router.post(
    "/resource:query",
    response_model=ResourceQueryResponse,
    summary="Atomically query any resource within a sandbox"
)
async def query_resource(
    sandbox: Sandbox = Depends(get_sandbox),
    request: ResourceQueryRequest = Body(...),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """
    The single entry point for all data queries in the editor.
    Executes a list of path queries atomically and returns the results.
    """
    try:
        query_results = await editor_utils.execute_queries(sandbox, request.paths)
        return ResourceQueryResponse(results=query_results)
    except Exception as e:
        logger.error(f"Unexpected error during query for sandbox {sandbox.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during query.")


# --- [核心] 统一资源修改API ---

@editor_router.post(
    "/resource:mutate",
    response_model=MutateResourceResponse,
    summary="Atomically mutate any resource within a sandbox"
)
async def mutate_resource(
    sandbox: Sandbox = Depends(get_sandbox),
    request: MutateResourceRequest = Body(...),
    editor_utils: EditorUtilsServiceInterface = Depends(Service("editor_utils_service"))
):
    """
    The single entry point for all data modifications in the editor.
    Executes a list of mutations atomically.
    - Path format: 'scope/path/to/resource' (e.g., 'lore/graphs/main').
    - For 'moment' mutations, 'mutation_mode' determines if a new snapshot is created.
    """
    if not request.mutations:
        # 如果没有修改操作，直接返回当前状态
        return MutateResourceResponse(
            sandbox_id=sandbox.id,
            head_snapshot_id=sandbox.head_snapshot_id
        )

    try:
        updated_sandbox = await editor_utils.execute_mutations(sandbox, request.mutations)
        
        return MutateResourceResponse(
            sandbox_id=updated_sandbox.id,
            head_snapshot_id=updated_sandbox.head_snapshot_id
        )
    except (ValueError, TypeError, KeyError) as e:
        # 捕获服务层可能抛出的已知错误
        logger.warning(f"Mutation request failed for sandbox {sandbox.id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # 捕获未知错误
        logger.error(f"Unexpected error during mutation for sandbox {sandbox.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during mutation.")

