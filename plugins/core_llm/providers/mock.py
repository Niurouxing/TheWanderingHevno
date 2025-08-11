# plugins/core_llm/providers/mock.py

import asyncio
from typing import Any

from .base import LLMProvider
from ..contracts import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)

class MockProvider(LLMProvider):
    """
    一个用于测试和调试的模拟 LLM 提供商。
    它会返回一个预设的响应，而不会进行任何外部调用。
    """
    @classmethod
    def requires_api_key(cls) -> bool:
        """声明此提供商不需要 API 密钥。"""
        return False

    async def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        api_key: str, # 仍然接收此参数，但会忽略它
        **kwargs: Any
    ) -> LLMResponse:
        """
        生成一个模拟响应。
        """
        await asyncio.sleep(0.05) # 模拟网络延迟
        mock_content = f"[MOCK RESPONSE for {model_name}] - Prompt received: '{prompt[:150]}...'"
        
        return LLMResponse(
            status=LLMResponseStatus.SUCCESS,
            content=mock_content,
            model_name=model_name,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 15, "total_tokens": len(prompt.split()) + 15}
        )

    def translate_error(self, ex: Exception) -> LLMError:
        """
        将异常转换为标准的 LLMError。
        对于模拟提供商，此方法不太可能被调用。
        """
        return LLMError(
            error_type=LLMErrorType.UNKNOWN_ERROR,
            message=f"An unexpected error occurred in MockProvider: {ex}",
            is_retryable=False
        )