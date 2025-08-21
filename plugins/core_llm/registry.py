# plugins/core_llm/registry.py

from typing import Dict, Type, Optional, List
from collections import defaultdict
import logging

from .providers.base import LLMProvider


logger = logging.getLogger(__name__)

class ProviderRegistry:
    """
    负责注册和查找 LLMProvider 的【实例】。
    它现在还负责构建一个“能力图谱”，用于反向查找哪个供应商能提供特定的规范模型。
    它的实例由 DI 容器管理。
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        # 我们仍然需要一个地方来存储元数据，比如环境变量名
        self._provider_env_vars: Dict[str, str] = {}
        # 能力图谱: Dict[canonical_model_name, List[provider_name]]
        self._capability_map: Dict[str, List[str]] = defaultdict(list)

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

    def unregister(self, name: str):
        """从注册表中注销一个提供商并立即重建能力图谱。"""
        if name in self._providers:
            self._providers.pop(name, None)
            self._provider_env_vars.pop(name, None)
            logger.info(f"LLM Provider instance '{name}' unregistered.")
            # --- [核心修复] ---
            # 在注销后，立即重建能力图谱，以确保状态一致。
            self.build_capability_map()
        else:
            logger.warning(f"Attempted to unregister a non-existent provider: '{name}'.")

    def build_capability_map(self):
        """
        遍历所有已注册的供应商，构建从规范模型名称到供应商列表的映射。
        这个方法应该在所有供应商都注册完毕后调用一次。
        """
        self._capability_map.clear()
        logger.debug("Building LLM provider capability map...")
        for provider_name, provider_instance in self._providers.items():
            # 检查提供商是否有模型映射配置
            if hasattr(provider_instance, 'model_mapping') and provider_instance.model_mapping:
                # model_mapping 的格式是 {proxy_name: canonical_name}
                # 我们关心的是 canonical_name
                for canonical_name in provider_instance.model_mapping.values():
                    if provider_name not in self._capability_map[canonical_name]:
                        self._capability_map[canonical_name].append(provider_name)
                        logger.debug(f"Mapped canonical model '{canonical_name}' to proxy provider '{provider_name}'.")
        logger.info("LLM provider capability map built successfully.")

    # --- 【新方法】 ---
    def get_providers_for_model(self, model_name: str) -> List[str]:
        """
        根据一个规范的模型名称，返回所有通过别名声明可以提供此模型的供应商列表。
        """
        return self._capability_map.get(model_name, [])