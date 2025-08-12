# plugins/core_llm/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List

from ..contracts import LLMResponse, LLMError


class LLMProvider(ABC):
    """
    一个抽象基-类，定义了所有 LLM 提供商适配器的标准接口。
    """
    @classmethod
    def requires_api_key(cls) -> bool:
        """
        声明此提供商是否需要 API 密钥才能工作。
        如果此方法返回 False，LLM 服务将不会尝试为此提供商从池中获取密钥。
        """
        return True

    @abstractmethod
    async def generate(
        self,
        *,
        messages: List[Dict[str, Any]],
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        """
        与 LLM 提供商进行交互以生成内容。

        这个方法必须处理所有可能的成功和“软失败”（如内容过滤）场景，
        并将它们封装在标准的 LLMResponse 对象中。
        如果发生无法处理的硬性错误（如网络问题、认证失败），它应该抛出原始异常，
        以便上层服务可以捕获并使用 translate_error 进行处理。

        :param messages: 发送给模型的结构化消息列表。
        :param model_name: 要使用的具体模型名称 (e.g., 'gemini-1.5-pro-latest')。
        :param api_key: 用于本次请求的 API 密钥。
        :param kwargs: 其他特定于提供商的参数 (e.g., temperature, max_tokens)。
        :return: 一个标准的 LLMResponse 对象。
        :raises Exception: 任何未被处理的、需要由 translate_error 解析的硬性错误。
        """
        pass

    @abstractmethod
    def translate_error(self, ex: Exception) -> LLMError:
        """
        将特定于提供商的原始异常转换为我们标准化的 LLMError 对象。

        这个方法是解耦的关键，它将具体的 SDK 错误与我们系统的内部错误处理逻辑分离开。

        :param ex: 从 generate 方法捕获的原始异常。
        :return: 一个标准的 LLMError 对象。
        """
        pass