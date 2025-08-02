# backend/runtimes/reporters.py
from typing import Any, Dict, Type
from backend.core.reporting import Reportable
from backend.core.registry import runtime_registry
from backend.core.interfaces import RuntimeInterface

class RuntimeReporter(Reportable):
    
    @property
    def report_key(self) -> str:
        return "runtimes"

    async def generate_report(self) -> Any:
        report = []
        # 注意：这里我们不再需要一个特殊的自省接口，
        # 我们直接使用运行时类本身声明的元数据。
        for name, runtime_class in runtime_registry._registry.items():
            # 假设 RuntimeInterface 增加了 config_model, description, category
            # (这个设计依然很好，可以保留)
            config_model = getattr(runtime_class, 'config_model', None)
            
            report.append({
                "name": name,
                "description": getattr(runtime_class, 'description', "N/A"),
                "category": getattr(runtime_class, 'category', "General"),
                "config_schema": config_model.model_json_schema() if config_model else {}
            })
        return sorted(report, key=lambda x: x['name'])