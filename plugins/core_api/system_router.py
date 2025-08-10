# plugins/core_api/system_router.py

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

# 从后端核心导入依赖
from backend.core.dependencies import Service
from backend.core.contracts import HookManager

# 获取这个模块的 logger 实例
logger = logging.getLogger(__name__)

# --- 路径计算 (保持健壮) ---
# __file__ -> .../project_root/plugins/core_api/system_router.py
# .parent -> .../project_root/plugins/core_api
# .parent.parent -> .../project_root/plugins
PLUGINS_DIR = Path(__file__).resolve().parent.parent

# --- 路由器 1: 用于 /api/... (平台元信息API) ---
# 我们将所有相关的API都聚合到这个路由器下
system_api_router = APIRouter(
    prefix="/api",
    tags=["System Platform API"]
)

@system_api_router.get("/plugins/manifest", response_model=List[Dict[str, Any]], summary="Get All Plugin Manifests")
async def get_all_plugins_manifest():
    """
    Retrieves the manifest.json content for all discovered plugins.
    This provides a central way for the frontend to understand what capabilities
    are available on the backend.
    """
    if not PLUGINS_DIR.is_dir():
        return []

    manifests = []
    for plugin_path in PLUGINS_DIR.iterdir():
        if not plugin_path.is_dir() or plugin_path.name.startswith(('__', '.')):
            continue
        
        manifest_file = plugin_path / "manifest.json"
        if manifest_file.is_file():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifests.append(json.load(f))
            except json.JSONDecodeError:
                logger.warning(f"Could not parse manifest.json for plugin: {plugin_path.name}")
                pass
    return manifests

@system_api_router.get("/system/hooks/manifest", response_model=Dict[str, List[str]], summary="Get Backend Hooks Manifest")
async def get_backend_hooks_manifest(
    hook_manager: HookManager = Depends(Service("hook_manager"))
):
    """
    Retrieves a list of all hook names that have been registered on the backend.
    Useful for frontend diagnostics and understanding event flow.
    """
    # ._hooks is an implementation detail, but for a diagnostics endpoint, it's acceptable.
    return {"hooks": list(hook_manager._hooks.keys())}


# --- 路由器 2: 用于 /plugins/... (服务前端插件的静态资源) ---
# 这个路由器没有前缀，因为它需要匹配根URL路径
frontend_assets_router = APIRouter(
    tags=["System Frontend Assets"]
)

@frontend_assets_router.get("/plugins/{plugin_id}/{resource_path:path}")
async def serve_plugin_resource(plugin_id: str, resource_path: str):
    """
    Dynamically serves static assets (like JS, CSS, images) from any plugin's
    directory. This is crucial for enabling frontend components of plugins.
    """
    logger.info(f"[ASSET_SERVER] Request for: /plugins/{plugin_id}/{resource_path}")
    
    try:
        if ".." in plugin_id or "\\" in plugin_id:
            logger.warning(f"[ASSET_SERVER] Invalid plugin ID detected: {plugin_id}")
            raise HTTPException(status_code=400, detail="Invalid plugin ID.")
        
        plugin_base_path = (PLUGINS_DIR / plugin_id).resolve()
        target_file_path = (plugin_base_path / resource_path).resolve()

        # Security check: Ensure the resolved path is still within the plugin's directory
        is_safe = str(target_file_path).startswith(str(plugin_base_path))
        if not is_safe:
            logger.warning(f"[ASSET_SERVER] Forbidden access attempt: {plugin_id}/{resource_path}")
            raise HTTPException(status_code=403, detail="Forbidden: Access outside of plugin directory is not allowed.")

        if not target_file_path.is_file():
            raise HTTPException(status_code=404, detail=f"Resource '{resource_path}' not found in plugin '{plugin_id}'.")

        logger.info(f"[ASSET_SERVER] Success! Serving file: {target_file_path}")
        return FileResponse(target_file_path)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[ASSET_SERVER] Error serving plugin resource '{plugin_id}/{resource_path}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while serving plugin resource.")