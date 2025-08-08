# plugins/core_diagnostics/auditor.py

import asyncio
from .contracts import Reportable
from typing import Any, Dict, List

class Auditor:
    def __init__(self, reporters: List[Reportable]):
        self._reporters = reporters
        self._static_report_cache: Dict[str, Any] | None = None

    def set_reporters(self, reporters: List[Reportable]):
        self._reporters = reporters
        self._static_report_cache = None

    async def generate_full_report(self) -> Dict[str, Any]:
        full_report = {}
        if self._static_report_cache is None:
            self._static_report_cache = await self._generate_static_reports()
        full_report.update(self._static_report_cache)

        dynamic_reports = await self._generate_dynamic_reports()
        full_report.update(dynamic_reports)
        return full_report

    async def _generate_reports_by_type(self, static: bool) -> Dict[str, Any]:
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