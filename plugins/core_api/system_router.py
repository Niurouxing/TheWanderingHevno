# plugins/core_api/system_router.py

import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse # <-- 导入 FileResponse

# 解析路径到项目根目录
# __file__ -> plugins/core_api/system_router.py
# .parent.parent.parent -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS_DIR = PROJECT_ROOT / "plugins"

# --- 路由器 1: 用于 /api/plugins/... ---
api_plugins_router = APIRouter(
    prefix="/api/plugins",
    tags=["Plugins", "System"]
)

@api_plugins_router.get("/manifest", response_model=List[Dict[str, Any]], summary="Get All Plugin Manifests")
async def get_all_plugins_manifest():
    """
    扫描 'plugins' 目录，聚合所有插件的 manifest.json 文件内容。
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
                pass
    return manifests

# --- 路由器 2: 【新】用于 /plugins/... (服务静态资源) ---
frontend_assets_router = APIRouter(
    tags=["System", "Frontend Assets"]
)

@frontend_assets_router.get("/plugins/{plugin_id}/{resource_path:path}")
async def serve_plugin_resource(plugin_id: str, resource_path: str):
    """
    动态服务任何前端插件的任何静态资源。
    此端点会将 /plugins/{id}/{path} 映射到服务器上的 [PROJECT_ROOT]/plugins/{id}/{path} 文件。
    """
    try:
        if ".." in plugin_id or "\\" in plugin_id:
            raise HTTPException(status_code=400, detail="Invalid plugin ID.")
        
        plugin_base_path = (PLUGINS_DIR / plugin_id).resolve()
        target_file_path = (plugin_base_path / resource_path).resolve()

        if not str(target_file_path).startswith(str(plugin_base_path)):
            raise HTTPException(status_code=403, detail="Forbidden: Access outside of plugin directory is not allowed.")

        if not target_file_path.is_file():
            raise HTTPException(status_code=404, detail=f"Resource '{resource_path}' not found in plugin '{plugin_id}'.")

        return FileResponse(target_file_path)

    except HTTPException as e:
        raise e
    except Exception as e:
        # 在生产环境中，应该记录一条错误日志
        # logger.error(...)
        raise HTTPException(status_code=500, detail="Internal server error while serving plugin resource.")