# plugins/core_api/system_router.py

import json
import logging # <-- 导入 logging
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException,Depends
from fastapi.responses import FileResponse


# 获取这个模块的 logger 实例
logger = logging.getLogger(__name__)

# --- 路径计算 (更健壮的方式) ---
# __file__ -> .../project_root/plugins/core_api/system_router.py
# .parent -> .../project_root/plugins/core_api
# .parent.parent -> .../project_root/plugins
# 这种方式比计算项目根再往下找更直接，更不容易出错。
PLUGINS_DIR = Path(__file__).resolve().parent.parent

# --- 路由器 1: 用于 /api/plugins/... ---
api_plugins_router = APIRouter(
    prefix="/api/plugins",
    tags=["Plugins", "System"]
)

@api_plugins_router.get("/manifest", response_model=List[Dict[str, Any]], summary="Get All Plugin Manifests")
async def get_all_plugins_manifest():
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

# --- 路由器 2: 用于 /plugins/... (服务静态资源) ---
frontend_assets_router = APIRouter(
    tags=["System", "Frontend Assets"]
)

@frontend_assets_router.get("/plugins/{plugin_id}/{resource_path:path}")
async def serve_plugin_resource(plugin_id: str, resource_path: str):
    """
    动态服务任何前端插件的任何静态资源。
    """
    # --- 【日志1】确认请求是否到达这里 ---
    logger.info(f"[ASSET_SERVER] Received request for: /plugins/{plugin_id}/{resource_path}")
    
    try:
        if ".." in plugin_id or "\\" in plugin_id:
            logger.warning(f"[ASSET_SERVER] Invalid plugin ID detected: {plugin_id}")
            raise HTTPException(status_code=400, detail="Invalid plugin ID.")
        
        # --- 【日志2】打印计算出的基准目录 ---
        logger.debug(f"[ASSET_SERVER] PLUGINS_DIR base path: {PLUGINS_DIR}")
        
        # 1. 构建目标文件的路径
        plugin_base_path = (PLUGINS_DIR / plugin_id).resolve()
        target_file_path = (plugin_base_path / resource_path).resolve()

        # --- 【日志3】打印计算出的完整路径 ---
        logger.debug(f"[ASSET_SERVER] Attempting to serve file from path: {target_file_path}")

        # 2. 安全性：验证解析后的路径是否仍在合法的插件目录内
        # --- 【日志4】打印安全检查的细节 ---
        is_safe = str(target_file_path).startswith(str(plugin_base_path))
        logger.debug(f"[ASSET_SERVER] Security check: Is path safe? {is_safe}")
        if not is_safe:
            logger.warning(f"[ASSET_SERVER] Forbidden access attempt: {plugin_id}/{resource_path}")
            raise HTTPException(status_code=403, detail="Forbidden: Access outside of plugin directory is not allowed.")

        # 3. 检查文件是否存在
        # --- 【日志5】打印文件存在性检查的结果 ---
        file_exists = target_file_path.is_file()
        logger.debug(f"[ASSET_SERVER] Final check: Does file exist? {file_exists}")
        if not file_exists:
            raise HTTPException(status_code=404, detail=f"Resource '{resource_path}' not found in plugin '{plugin_id}'.")

        # 4. 返回文件响应
        logger.info(f"[ASSET_SERVER] Success! Serving file: {target_file_path}")
        return FileResponse(target_file_path)

    except HTTPException as e:
        # 重新抛出已知的 HTTP 异常，这样 FastAPI 会处理它
        raise e
    except Exception as e:
        logger.error(f"[ASSET_SERVER] Error serving plugin resource '{plugin_id}/{resource_path}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while serving plugin resource.")

