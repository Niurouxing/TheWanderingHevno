# plugins/core_llm/providers/gemini.py

from typing import Any
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai import types as generation_types

# --- 核心修改: 导入路径修正 ---
from .base import LLMProvider
from ..contracts import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)

class GeminiProvider(LLMProvider):
    """
    针对 Google Gemini API 的 LLMProvider 实现。
    """

    async def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        try:
            # 每次调用都独立配置，以支持多密钥轮换
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(model_name)

            # 提取支持的生成配置
            generation_config = {
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "max_output_tokens": kwargs.get("max_tokens"),
            }
            # 清理 None 值
            generation_config = {k: v for k, v in generation_config.items() if v is not None}

            response: generation_types.GenerateContentResponse = await model.generate_content_async(
                contents=prompt,
                generation_config=generation_config
            )

            # 检查是否因安全策略被阻止
            if not response.parts:
                if response.prompt_feedback.block_reason:
                    error_message = f"Request blocked due to {response.prompt_feedback.block_reason.name}"
                    return LLMResponse(
                        status=LLMResponseStatus.FILTERED,
                        model_name=model_name,
                        error_details=LLMError(
                            error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                            message=error_message,
                            is_retryable=False
                        )
                    )

            # 提取 token 使用情况
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
            
            return LLMResponse(
                status=LLMResponseStatus.SUCCESS,
                content=response.text,
                model_name=model_name,
                usage=usage
            )

        except generation_types.StopCandidateException as e:
            # 这种情况也属于内容过滤
            return LLMResponse(
                status=LLMResponseStatus.FILTERED,
                model_name=model_name,
                error_details=LLMError(
                    error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                    message=f"Generation stopped due to safety settings: {e}",
                    is_retryable=False,
                )
            )

    def translate_error(self, ex: Exception) -> LLMError:
        """
        将 Google API 的异常转换为标准的 LLMError。
        """
        error_details = {"provider": "gemini", "exception": type(ex).__name__, "message": str(ex)}

        if isinstance(ex, google_exceptions.PermissionDenied):
            return LLMError(
                error_type=LLMErrorType.AUTHENTICATION_ERROR,
                message="Invalid API key or insufficient permissions.",
                is_retryable=False,
                provider_details=error_details,
            )
        
        if isinstance(ex, google_exceptions.ResourceExhausted):
            return LLMError(
                error_type=LLMErrorType.RATE_LIMIT_ERROR,
                message="Rate limit exceeded. Please try again later or use a different key.",
                is_retryable=False,
                provider_details=error_details,
            )

        # --- vvv START: 关键修改 vvv ---
        if isinstance(ex, google_exceptions.InvalidArgument):
            # 检查具体的错误消息，因为 InvalidArgument 可能有很多原因
            if "API key not valid" in str(ex):
                return LLMError(
                    error_type=LLMErrorType.AUTHENTICATION_ERROR,
                    message=f"The provided API key is invalid. Details: {ex}",
                    is_retryable=False, # 认证失败不应该重试同一个密钥
                    provider_details=error_details,
                )
            
            # 如果是其他类型的 InvalidArgument，则按原逻辑处理
            return LLMError(
                error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                message=f"Invalid argument provided to the API. Check model name and parameters. Details: {ex}",
                is_retryable=False,
                provider_details=error_details,
            )
        # --- ^^^ END: 关键修改 ^^^ ---

        if isinstance(ex, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
            return LLMError(
                error_type=LLMErrorType.PROVIDER_ERROR,
                message="The service is temporarily unavailable or the request timed out. Please try again.",
                is_retryable=True,
                provider_details=error_details,
            )
            
        if isinstance(ex, google_exceptions.GoogleAPICallError):
            return LLMError(
                error_type=LLMErrorType.NETWORK_ERROR,
                message=f"A network-level error occurred while communicating with Google API: {ex}",
                is_retryable=True,
                provider_details=error_details,
            )

        return LLMError(
            error_type=LLMErrorType.UNKNOWN_ERROR,
            message=f"An unknown error occurred with the Gemini provider: {ex}",
            is_retryable=False,
            provider_details=error_details,
        )