# plugins/core_llm/providers/gemini.py

from typing import Any, List, Dict
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from google.generativeai import types as generation_types

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
        messages: List[Dict[str, Any]],
        model_name: str,
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            generation_config = {
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "max_output_tokens": kwargs.get("max_tokens"),
            }
            generation_config = {k: v for k, v in generation_config.items() if v is not None}

            provider_messages = []
            for msg in messages:
                # The Gemini SDK expects {"role": "...", "parts": ["..."]}
                provider_messages.append({"role": msg["role"], "parts": [str(msg["content"])]})

            response: generation_types.GenerateContentResponse = await model.generate_content_async(
                contents=provider_messages, # Use the translated messages
                generation_config=generation_config
            )

            if not response.parts:
                if response.prompt_feedback.block_reason:
                    error_message = f"Request blocked due to {response.prompt_feedback.block_reason.name}"
                    return LLMResponse(status=LLMResponseStatus.FILTERED, model_name=model_name, error_details=LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message=error_message, is_retryable=False))

            usage = {"prompt_tokens": response.usage_metadata.prompt_token_count, "completion_tokens": response.usage_metadata.candidates_token_count, "total_tokens": response.usage_metadata.total_token_count}
            
            return LLMResponse(status=LLMResponseStatus.SUCCESS, content=response.text, model_name=model_name, usage=usage)

        except generation_types.StopCandidateException as e:
            return LLMResponse(status=LLMResponseStatus.FILTERED, model_name=model_name, error_details=LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message=f"Generation stopped due to safety settings: {e}", is_retryable=False))

    def translate_error(self, ex: Exception) -> LLMError:
        # This part of the code remains unchanged.
        error_details = {"provider": "gemini", "exception": type(ex).__name__, "message": str(ex)}
        if isinstance(ex, google_exceptions.PermissionDenied):
            return LLMError(error_type=LLMErrorType.AUTHENTICATION_ERROR, message="Invalid API key or insufficient permissions.", is_retryable=False, provider_details=error_details)
        if isinstance(ex, google_exceptions.ResourceExhausted):
            return LLMError(error_type=LLMErrorType.RATE_LIMIT_ERROR, message="Rate limit exceeded. Please try again later or use a different key.", is_retryable=False, provider_details=error_details)
        if isinstance(ex, google_exceptions.InvalidArgument):
            if "API key not valid" in str(ex):
                return LLMError(error_type=LLMErrorType.AUTHENTICATION_ERROR, message=f"The provided API key is invalid. Details: {ex}", is_retryable=False, provider_details=error_details)
            return LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message=f"Invalid argument provided to the API. Check model name and parameters. Details: {ex}", is_retryable=False, provider_details=error_details)
        if isinstance(ex, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
            return LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="The service is temporarily unavailable or the request timed out. Please try again.", is_retryable=True, provider_details=error_details)
        if isinstance(ex, google_exceptions.GoogleAPICallError):
            return LLMError(error_type=LLMErrorType.NETWORK_ERROR, message=f"A network-level error occurred while communicating with Google API: {ex}", is_retryable=True, provider_details=error_details)
        return LLMError(error_type=LLMErrorType.UNKNOWN_ERROR, message=f"An unknown error occurred with the Gemini provider: {ex}", is_retryable=False, provider_details=error_details)