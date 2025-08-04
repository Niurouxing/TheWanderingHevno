# plugins/core_api/system_router.py
import json
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

# 这是一个更健壮的寻找项目根目录的方式
# 假设此文件在 PROJECT_ROOT/plugins/core_api/system_router.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

HEVNO_JSON_PATH = PROJECT_ROOT / "hevno.json"

router = APIRouter(
    prefix="/api/plugins",
    tags=["Plugins", "System"]
)

@router.get("/manifest", response_model=List[Dict[str, Any]], summary="Get Frontend Plugin Manifests")
async def get_plugins_manifest_for_frontend():
    """
    从 hevno.json 读取插件定义，并将其格式化为前端内核期望的列表。
    这是前端动态加载和贡献系统的唯一事实来源。
    """
    if not HEVNO_JSON_PATH.is_file():
        raise HTTPException(status_code=404, detail=f"Manifest file 'hevno.json' not found at project root: {HEVNO_JSON_PATH}")

    with open(HEVNO_JSON_PATH, "r", encoding='utf-8') as f:
        manifest_data = json.load(f)

    plugins_list = []
    for name, plugin_data in manifest_data.get("plugins", {}).items():
        # 我们将插件名称和其所有数据捆绑在一起
        plugins_list.append({
            "id": name,  # 使用字典键作为唯一ID
            **plugin_data
        })

    return plugins_list