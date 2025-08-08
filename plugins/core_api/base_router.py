# plugins/core_api/base_router.py

from typing import List, Dict 
from fastapi import APIRouter, Depends

from backend.core.dependencies import Service
from backend.core.contracts import HookManager

from plugins.core_diagnostics.contracts import AuditorInterface

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/system/report")
async def get_system_report(auditor: AuditorInterface = Depends(Service("auditor"))):
    """获取完整的系统状态和元数据报告。"""
    return await auditor.generate_full_report()

@router.get("/system/hooks/manifest", response_model=Dict[str, List[str]], summary="Get Backend Hooks Manifest")
async def get_backend_hooks_manifest(
    hook_manager: HookManager = Depends(Service("hook_manager"))
):
    """获取一个包含所有已在后端注册的钩子名称的列表。"""
    return {"hooks": list(hook_manager._hooks.keys())}