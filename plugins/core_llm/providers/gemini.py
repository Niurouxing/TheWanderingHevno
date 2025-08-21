# plugins/core_llm/providers/gemini.py

from typing import Any, List, Dict
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
# --- [新] 导入Gemini SDK的类型定义 ---
from google.generativeai import types as generation_types
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import LLMProvider
from ..contracts import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)

# --- [新] 定义固定的安全设置 ---
# 将所有类别设置为 BLOCK_NONE，等同于用户要求的 'OFF'
FIXED_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    # HARM_CATEGORY_CIVIC_INTEGRITY 似乎在最新的SDK中不直接作为可配置的HARM_CATEGORY，
    # 但前四个是核心。如果SDK更新，可以再添加。
}


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
            
            system_instruction = None
            provider_messages = []
            
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                
                if role == "system":
                    if system_instruction is None:
                        system_instruction = ""
                    system_instruction += str(content) + "\n"
                elif role in ["user", "model"]:
                    provider_messages.append({"role": role, "parts": [str(content)]})
            
            # 从 kwargs 中提取所有与生成相关的参数
            generation_config_params = {
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "top_k": kwargs.get("top_k"),
                "max_output_tokens": kwargs.get("max_output_tokens"), # 使用新名称
                "candidate_count": 1 # 保持固定
            }
            # 移除值为None的参数
            generation_config_params = {k: v for k, v in generation_config_params.items() if v is not None}
            
            thinking_config_dict = kwargs.get("thinking_config")
            if isinstance(thinking_config_dict, dict):
                # 将其转换为SDK要求的ThinkingConfig对象
                generation_config_params["thinking_config"] = generation_types.ThinkingConfig(
                    include_thoughts=thinking_config_dict.get('include_thoughts', True),
                    thinking_budget=thinking_config_dict.get('thinking_budget')
                )

            # --- [核心修改 1/3] ---
            # 构建一个用于日志记录的、包含所有最终参数的字典。
            final_request_for_log = {
                "model_name": model_name,
                "system_instruction": system_instruction.strip() if system_instruction else None,
                "messages": provider_messages,
                "generation_config": generation_config_params,
                # 为了日志可读性，将枚举转换为字符串
                "safety_settings": {k.name: v.name for k, v in FIXED_SAFETY_SETTINGS.items()}
            }

            # --- 在实例化模型时传入安全设置 ---
            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_instruction.strip() if system_instruction else None,
                safety_settings=FIXED_SAFETY_SETTINGS
            )

            # --- 在实例化模型时传入完整的生成配置 ---
            response: generation_types.GenerateContentResponse = await model.generate_content_async(
                contents=provider_messages,
                generation_config=generation_config_params if generation_config_params else None
            )

            if not response.parts:
                if response.prompt_feedback.block_reason:
                    error_message = f"Request blocked due to {response.prompt_feedback.block_reason.name}"
                    error = LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message=error_message, is_retryable=False)
                    # --- [核心修改 2/3] ---
                    # 在返回错误响应时，也附上最终请求。
                    return LLMResponse(status=LLMResponseStatus.FILTERED, model_name=model_name, error_details=error, final_request_payload=final_request_for_log)
                else:
                    error = LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Provider returned an empty response without a clear reason.", is_retryable=True)
                    return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error, final_request_payload=final_request_for_log)


            usage = {"prompt_tokens": response.usage_metadata.prompt_token_count, "completion_tokens": response.usage_metadata.candidates_token_count, "total_tokens": response.usage_metadata.total_token_count}
            
            # --- [核心修改 3/3] ---
            # 在返回成功响应时，附上最终请求。
            return LLMResponse(
                status=LLMResponseStatus.SUCCESS, 
                content=response.text, 
                model_name=model_name, 
                usage=usage,
                final_request_payload=final_request_for_log
            )

        except generation_types.StopCandidateException as e:
            error = LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message=f"Generation stopped due to safety settings: {e}", is_retryable=False)
            # 即使在这种异常中，我们也尝试返回请求日志
            return LLMResponse(status=LLMResponseStatus.FILTERED, model_name=model_name, error_details=error, final_request_payload=locals().get('final_request_for_log'))

    def translate_error(self, ex: Exception) -> LLMError:
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