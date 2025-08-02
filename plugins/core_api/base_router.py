# plugins/core_api/base_router.py

from fastapi import APIRouter, Depends
from .dependencies import get_auditor
from .auditor import Auditor

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/system/report")
async def get_system_report(auditor: Auditor = Depends(get_auditor)):
    """获取完整的系统状态和元数据报告。"""
    return await auditor.generate_full_report()