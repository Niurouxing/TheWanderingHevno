# plugins/core_api/base_router.py

from typing import List, Dict 
from fastapi import APIRouter, Depends

from backend.core.dependencies import Service
from backend.core.contracts import HookManager

# 【修复第一步】: 删除这个非法的跨插件导入
# from plugins.core_diagnostics.contracts import AuditorInterface

router = APIRouter(prefix="/api", tags=["System"])

# 【修复第二步】: 移除 auditor 参数的类型提示。
# 依赖注入仍然可以通过 Service("auditor") 正常工作。
@router.get("/system/report")
async def get_system_report(auditor = Depends(Service("auditor"))):
    """获取完整的系统状态和元数据报告。"""
    # 尽管没有了类型提示，auditor 对象仍然会被正确注入
    return await auditor.generate_full_report()

@router.get("/system/hooks/manifest", response_model=Dict[str, List[str]], summary="Get Backend Hooks Manifest")
async def get_backend_hooks_manifest(
    hook_manager: HookManager = Depends(Service("hook_manager"))
):
    """获取一个包含所有已在后端注册的钩子名称的列表。"""
    return {"hooks": list(hook_manager._hooks.keys())}