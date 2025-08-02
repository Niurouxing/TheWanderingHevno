# plugins/core_llm/reporters.py
from typing import Any, Dict
from backend.core.reporting import Reportable
from plugins.core_llm.registry import provider_registry

class LLMProviderReporter(Reportable):
    
    @property
    def report_key(self) -> str:
        return "llm_providers"
    
    async def generate_report(self) -> Any:
        manifest = []
        all_info = provider_registry.get_all_provider_info()
        for name, info in all_info.items():
            provider_class = info.provider_class
            manifest.append({
                "name": name,
                # 同样，假设 LLMProvider 基类增加了 supported_models 属性
                "supported_models": getattr(provider_class, 'supported_models', [])
            })
        return sorted(manifest, key=lambda x: x['name'])