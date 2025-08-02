# backend/api/base_router.py

from fastapi import APIRouter, Depends, Request
from backend.core.reporting import Auditor

router = APIRouter()

# 这是一个示例，展示了依赖注入仍然可以工作，尽管函数定义在别处
def get_auditor(request: Request) -> Auditor:
    return request.app.state.auditor

@router.get("/")
def read_root():
    return {"message": "Hevno Backend is running on a factory-pattern architecture!"}

@router.get("/api/system/report", tags=["System"])
async def get_system_report(auditor: Auditor = Depends(get_auditor)):
    return await auditor.generate_full_report()