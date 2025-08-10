# plugins/core_diagnostics/api.py

from fastapi import APIRouter, Depends
from backend.core.dependencies import Service
from .contracts import AuditorInterface # 在插件内部导入自己的契约是允许的

diagnostics_router = APIRouter(
    prefix="/api/system", # 保持URL不变，或者改为 /api/diagnostics
    tags=["System", "Diagnostics"]
)

@diagnostics_router.get("/report", summary="Get full system diagnostics report")
async def get_system_report(
    # 正确的方式：通过DI容器按名称解析服务
    auditor: AuditorInterface = Depends(Service("auditor"))
):
    """
    Generates and returns a comprehensive report on the system's state,
    including loaded plugins, registered runtimes, and other metadata.
    """
    return await auditor.generate_full_report()