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
        provider_names = self._provider_registry.get_all_provider_names()
        return sorted(provider_names)