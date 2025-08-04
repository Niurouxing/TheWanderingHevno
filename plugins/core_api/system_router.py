# plugins/core_api/system_router.py
import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

# 解析路径到项目根目录，然后定位到 'plugins' 文件夹
# __file__ -> plugins/core_api/system_router.py
# .parent.parent.parent -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS_DIR = PROJECT_ROOT / "plugins"

router = APIRouter(
    prefix="/api/plugins",
    tags=["Plugins", "System"]
)

@router.get("/manifest", response_model=List[Dict[str, Any]], summary="Get All Plugin Manifests")
async def get_all_plugins_manifest():
    """
    扫描 'plugins' 目录，聚合所有插件的 manifest.json 文件内容。
    这为前端提供了所有插件元数据的唯一、完整的事实来源。
    """
    if not PLUGINS_DIR.is_dir():
        return []

    manifests = []
    for plugin_path in PLUGINS_DIR.iterdir():
        # 忽略非目录或特殊目录 (如 __pycache__)
        if not plugin_path.is_dir() or plugin_path.name.startswith(('__', '.')):
            continue
        
        manifest_file = plugin_path / "manifest.json"
        if manifest_file.is_file():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifests.append(json.load(f))
            except json.JSONDecodeError:
                # 在生产环境中，应该记录一条警告日志
                # logger.warning(f"Could not parse manifest.json for plugin: {plugin_path.name}")
                pass
    return manifests