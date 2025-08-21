# plugins/core_llm/providers/openai_compatible.py
import httpx
import json
import os
from typing import Any, List, Dict, Optional

from .base import LLMProvider
from ..contracts import (
    LLMResponse,
    LLMError,
    LLMResponseStatus,
    LLMErrorType,
)

class OpenAICompatibleProvider(LLMProvider):
    """
    一个通用的 LLMProvider，用于与任何遵循 OpenAI Chat Completions API 规范的
    自定义终结点进行交互。
    """
    def __init__(self, base_url: str, model_mapping: Dict[str, str] = None):
        if not base_url:
            raise ValueError("OpenAICompatibleProvider requires a 'base_url'.")
        # 直接使用提供的 base_url，只移除末尾可能存在的斜杠
        self.base_url = base_url.rstrip('/')
        
        self.model_mapping = model_mapping or {}
        # 创建反向映射，用于从规范名称找到代理名称
        # 格式: { "gemini/gemini-1.5-pro": "my-gemini-proxy-name", ... }
        self._reverse_model_mapping = {v: k for k, v in self.model_mapping.items()}
        
        self.http_client = httpx.AsyncClient(timeout=120.0)

    def get_underlying_model(self, model_name: str) -> Optional[str]:
        """根据配置的映射返回模型的"真实"身份。"""
        # model_name 在这里是代理名称 (e.g., 'chat_model_pro')
        return self.model_mapping.get(model_name)

    async def generate(
        self,
        *,
        messages: List[Dict[str, Any]],
        model_name: str, # <-- 接收到的是完整的规范名称, e.g., "meta/llama3-70b-instruct"
        api_key: str,
        **kwargs: Any
    ) -> LLMResponse:
        
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # 使用完整的规范名称 (model_name) 在反向映射中查找提供商特定的名称。
        # 如果找不到，则说明没有为此模型配置别名，我们直接将规范名称的第二部分
        # (例如 "llama3-70b-instruct") 作为后备。
        provider_specific_model_name = self._reverse_model_mapping.get(model_name)
        if not provider_specific_model_name:
            # 后备逻辑：如果模型没有在 mapping 中明确指定，
            # 则尝试使用规范名称的第二部分。
            # 这使得用户可以添加一个 provider 而不必须为每个模型都创建别名。
            provider_specific_model_name = model_name.split('/')[-1]

        payload = {
            "model": provider_specific_model_name, # <-- 使用查找或后备的名称
            "messages": messages,
            "temperature": kwargs.get("temperature"),
            "max_tokens": kwargs.get("max_output_tokens"),
            "top_p": kwargs.get("top_p"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        
        final_request_for_log = {"endpoint": endpoint, "payload": payload}

        try:
            response = await self.http_client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            first_choice = data.get("choices", [{}])[0]
            content = first_choice.get("message", {}).get("content")
            
            usage_data = data.get("usage", {})
    
            # [核心修复] 创建一个新的字典，只包含值为整数的键值对，
            # 以确保与 LLMResponse 模型的 `usage: Dict[str, int]` 契约兼容。
            normalized_usage = {
                key: value
                for key, value in usage_data.items()
                if isinstance(value, int)
            }
            
            return LLMResponse(
                status=LLMResponseStatus.SUCCESS,
                content=content,
                model_name=data.get("model", model_name),
                usage=normalized_usage, # <-- 使用净化后的、保证兼容的usage对象
                final_request_payload=final_request_for_log
            )

        except httpx.HTTPStatusError as e:
            error = self.translate_error(e)
            return LLMResponse(
                status=LLMResponseStatus.ERROR,
                model_name=model_name,
                error_details=error,
                final_request_payload=final_request_for_log
            )
        except Exception as e:
            raise e

    def translate_error(self, ex: Exception) -> LLMError:
        error_details = {"provider": "openai_compatible", "exception": type(ex).__name__, "message": str(ex)}
        
        if isinstance(ex, httpx.HTTPStatusError):
            status_code = ex.response.status_code
            if status_code == 401:
                return LLMError(error_type=LLMErrorType.AUTHENTICATION_ERROR, message="Invalid API key provided.", is_retryable=False, provider_details=error_details)
            if status_code == 429:
                return LLMError(error_type=LLMErrorType.RATE_LIMIT_ERROR, message="Rate limit exceeded.", is_retryable=True, provider_details=error_details)
            if 400 <= status_code < 500:
                return LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message=f"Client error: {ex.response.text}", is_retryable=False, provider_details=error_details)
            if 500 <= status_code < 600:
                return LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message=f"Server error: {ex.response.text}", is_retryable=True, provider_details=error_details)

        if isinstance(ex, httpx.RequestError):
            return LLMError(error_type=LLMErrorType.NETWORK_ERROR, message=f"Network error: {ex}", is_retryable=True, provider_details=error_details)

        return LLMError(error_type=LLMErrorType.UNKNOWN_ERROR, message=f"An unknown error occurred: {ex}", is_retryable=False, provider_details=error_details)