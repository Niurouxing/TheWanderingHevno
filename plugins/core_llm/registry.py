# plugins/core_llm/registry.py

from typing import Dict, Type, Optional, Callable
from pydantic import BaseModel
from .providers.base import LLMProvider
import logging

logger = logging.getLogger(__name__)

class ProviderInfo(BaseModel):
    provider_class: Type[LLMProvider]
    key_env_var: str

class ProviderRegistry:
    """
    负责注册和查找 LLMProvider 实例及其元数据。
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._provider_info: Dict[str, ProviderInfo] = {}

    def register(self, name: str, key_env_var: str) -> Callable[[Type[LLMProvider]], Type[LLMProvider]]:
        def decorator(provider_class: Type[LLMProvider]) -> Type[LLMProvider]:
            if name in self._provider_info:
                logger.warning(f"Overwriting LLM provider registration for '{name}'.")
            self._provider_info[name] = ProviderInfo(provider_class=provider_class, key_env_var=key_env_var)
            logger.info(f"LLM Provider '{name}' discovered (keys from '{key_env_var}').")
            return provider_class
        return decorator
    
    def get_provider_info(self, name: str) -> Optional[ProviderInfo]:
        return self._provider_info.get(name)

    def instantiate_all(self):
        """实例化所有已注册的 Provider。"""
        for name, info in self._provider_info.items():
            if name not in self._providers:
                self._providers[name] = info.provider_class()
    
    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)
    
    def get_all_provider_info(self) -> Dict[str, ProviderInfo]:
        return self._provider_info

provider_registry = ProviderRegistry()