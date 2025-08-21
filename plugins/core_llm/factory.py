# plugins/core_llm/factory.py
from typing import Dict, Any, Optional
from .providers.base import LLMProvider
from .providers.openai_compatible import OpenAICompatibleProvider

class ProviderFactory:
    """管理单个 LLMProvider 实例的生命周期。"""
    def __init__(self, initial_config: Dict[str, Any]):
        self._config = initial_config
        self._provider_instance: Optional[LLMProvider] = None
        self._create_instance()

    def get_provider(self) -> LLMProvider:
        """获取或创建 Provider 实例。"""
        if self._provider_instance is None:
            self._create_instance()
        return self._provider_instance

    def _create_instance(self):
        """根据配置创建新的 Provider 实例。"""
        provider_type = self._config.get("type")
        if provider_type == "openai_compatible":
            self._provider_instance = OpenAICompatibleProvider(
                base_url=self._config.get("base_url"),
                model_mapping=self._config.get("model_mapping")
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def update_config_and_recreate(self, new_config: Dict[str, Any]):
        """使用新配置更新并销毁旧实例，下一次 get_provider() 将创建新实例。"""
        self._config = new_config
        self._provider_instance = None
