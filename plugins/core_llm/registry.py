# plugins/core_llm/registry.py

from typing import Dict, Type, Optional, List
from .providers.base import LLMProvider
import logging

logger = logging.getLogger(__name__)

class ProviderRegistry:
    """
    负责注册和查找 LLMProvider 的【实例】。
    它的实例由 DI 容器管理。
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        # 我们仍然需要一个地方来存储元数据，比如环境变量名
        self._provider_env_vars: Dict[str, str] = {}

    def register(self, name: str, provider_instance: LLMProvider, key_env_var: str):
        """向注册表注册一个 LLM 提供商的【实例】。"""
        if name in self._providers:
            logger.warning(f"Overwriting LLM provider instance for '{name}'.")
        self._providers[name] = provider_instance
        self._provider_env_vars[name] = key_env_var
        logger.info(f"LLM Provider instance '{name}' registered (keys from '{key_env_var}').")

    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)
        
    def get_key_env_var(self, name: str) -> Optional[str]:
        return self._provider_env_vars.get(name)

    def get_all_provider_names(self) -> List[str]:
        return list(self._providers.keys())