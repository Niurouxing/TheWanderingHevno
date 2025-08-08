# plugins/core_llm/reporters.py
from typing import Any
from plugins.core_diagnostics.contracts import Reportable
from .registry import ProviderRegistry


class LLMProviderReporter(Reportable):
    
    def __init__(self, provider_registry: ProviderRegistry):
        self._provider_registry = provider_registry

    @property
    def report_key(self) -> str:
        return "llm_providers"
    
    async def generate_report(self) -> Any:
        manifest = []
        all_info = self._provider_registry.get_all_provider_info()
        for name, info in all_info.items():
            provider_class = info.provider_class
            manifest.append({
                "name": name,
                "supported_models": getattr(provider_class, 'supported_models', [])
            })
        return sorted(manifest, key=lambda x: x['name'])