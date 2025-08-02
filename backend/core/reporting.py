# backend/core/reporting.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Type

class Reportable(ABC):
    """
    一个统一的汇报协议。
    任何希望向系统提供状态或元数据的组件都应实现此接口。
    """
    
    @property
    @abstractmethod
    def report_key(self) -> str:
        """
        返回此报告在最终JSON对象中的唯一键名。
        例如: "runtimes", "llm_providers", "system_stats"
        """
        pass

    @property
    def is_static(self) -> bool:
        """
        指明此报告是否为静态。
        True: 报告内容在应用启动后不变，可以被缓存。
        False: 报告内容是动态的，每次请求都需重新生成。
        默认值为静态。
        """
        return True

    @abstractmethod
    async def generate_report(self) -> Any:
        """
        生成并返回此组件的报告内容。
        内容可以是任何可以被JSON序列化的类型 (dict, list, str, etc.)。
        """
        pass

class AuditorRegistry:
    """一个简单的注册表，用于收集所有 Reportable 实例。"""
    def __init__(self):
        self._reportables: List[Reportable] = []

    def register(self, reportable: Reportable):
        """注册一个 Reportable 实例。"""
        print(f"Auditor: Registering reportable component with key '{reportable.report_key}'.")
        self._reportables.append(reportable)
    
    def get_all(self) -> List[Reportable]:
        return self._reportables

class Auditor:
    """
    审阅官服务。负责从注册表中收集所有报告并进行聚合。
    """
    def __init__(self, registry: AuditorRegistry):
        self._registry = registry
        self._static_report_cache: Dict[str, Any] | None = None

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

    async def _generate_static_reports(self) -> Dict[str, Any]:
        """仅生成并缓存所有静态报告。"""
        print("Auditor: Generating static report cache...")
        static_reports = {}
        tasks = []
        reportables = [r for r in self._registry.get_all() if r.is_static]
        for r in reportables:
            tasks.append(r.generate_report())
        
        results = await asyncio.gather(*tasks)
        
        for r, result in zip(reportables, results):
            static_reports[r.report_key] = result
        
        return static_reports

    async def _generate_dynamic_reports(self) -> Dict[str, Any]:
        """仅生成所有动态报告。"""
        dynamic_reports = {}
        tasks = []
        reportables = [r for r in self._registry.get_all() if r.is_static is False]
        if not reportables:
            return {}
            
        for r in reportables:
            tasks.append(r.generate_report())
        
        results = await asyncio.gather(*tasks)
        
        for r, result in zip(reportables, results):
            dynamic_reports[r.report_key] = result
            
        return dynamic_reports

# 全局单例
auditor_registry = AuditorRegistry()