# plugins/core_api/auditor.py

import asyncio
from .contracts import Reportable
from typing import Any, Dict, List


class Auditor:
    """
    审阅官服务。负责从注册的 Reportable 实例中收集报告并聚合。
    """
    def __init__(self, reporters: List[Reportable]):
        self._reporters = reporters
        self._static_report_cache: Dict[str, Any] | None = None

    def set_reporters(self, reporters: List[Reportable]):
        """允许在创建后设置/替换报告器列表。"""
        self._reporters = reporters
        self._static_report_cache = None

    async def generate_full_report(self) -> Dict[str, Any]:
        """生成完整的系统报告。"""
        full_report = {}

        # 1. 处理静态报告 (带缓存)
        if self._static_report_cache is None:
            self._static_report_cache = await self._generate_static_reports()
        full_report.update(self._static_report_cache)

        # 2. 处理动态报告 (实时生成)
        dynamic_reports = await self._generate_dynamic_reports()
        full_report.update(dynamic_reports)

        return full_report

    async def _generate_reports_by_type(self, static: bool) -> Dict[str, Any]:
        """根据报告类型（静态/动态）生成报告。"""
        reports = {}
        reportables_to_run = [r for r in self._reporters if r.is_static is static]
        if not reportables_to_run:
            return {}

        tasks = [r.generate_report() for r in reportables_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r, result in zip(reportables_to_run, results):
            if isinstance(result, Exception):
                reports[r.report_key] = {"error": f"Failed to generate report: {result}"}
            else:
                reports[r.report_key] = result
        return reports

    async def _generate_static_reports(self) -> Dict[str, Any]:
        return await self._generate_reports_by_type(static=True)

    async def _generate_dynamic_reports(self) -> Dict[str, Any]:
        return await self._generate_reports_by_type(static=False)