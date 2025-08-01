# backend/llm/service.py

import asyncio
from typing import Dict, Type, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.llm.providers.base import LLMProvider
from backend.llm.manager import KeyPoolManager, KeyInfo
from backend.llm.models import (
    LLMResponse,
    LLMError,
    LLMErrorType,
    LLMResponseStatus,
    LLMRequestFailedError,
)


class ProviderRegistry:
    """
    负责注册和查找 LLMProvider 实例。
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}

    def register(self, name: str, provider_instance: LLMProvider):
        if name in self._providers:
            pass
        self._providers[name] = provider_instance

    def get(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name)


class LLMService:
    """
    LLM Gateway 的核心服务，负责协调所有组件并执行请求。
    """
    def __init__(
        self,
        key_manager: KeyPoolManager,
        provider_registry: ProviderRegistry,
        max_retries: int = 3
    ):
        self.key_manager = key_manager
        self.provider_registry = provider_registry
        self.max_retries = max_retries

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        try:
            provider_name, actual_model_name = self._parse_model_name(model_name)
        except ValueError as e:
            return self._create_failure_response(
                model_name=model_name,
                error=LLMError(
                    error_type=LLMErrorType.INVALID_REQUEST_ERROR,
                    message=str(e),
                    is_retryable=False,
                ),
            )

        def log_before_sleep(retry_state):
            pass
        
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True,
            before_sleep=log_before_sleep
        )

        try:
            wrapped_attempt = retry_decorator(self._attempt_request)
            return await wrapped_attempt(provider_name, actual_model_name, prompt, **kwargs)
        
        except LLMRequestFailedError as e:
            final_message = (
                f"LLM request for model '{model_name}' failed after {self.max_retries} attempt(s)."
            )
            raise LLMRequestFailedError(
                final_message,
                last_error=e.last_error
            ) from e
        
        except Exception as e:
            raise

    async def _attempt_request(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise LLMRequestFailedError(f"Provider '{provider_name}' not found.")

        try:
            async with self.key_manager.acquire_key(provider_name) as key_info:
                try:
                    response = await provider.generate(
                        prompt=prompt, model_name=model_name, api_key=key_info.key_string, **kwargs
                    )
                    if response.status in [LLMResponseStatus.SUCCESS, LLMResponseStatus.FILTERED]:
                        return response
                    raise LLMRequestFailedError("Provider returned an error response.", last_error=response.error_details)
                
                except Exception as e:
                    llm_error = provider.translate_error(e)
                    await self._handle_error(provider_name, key_info, llm_error)
                    error_message = f"Request attempt failed: {llm_error.message}"
                    raise LLMRequestFailedError(error_message, last_error=llm_error) from e
        
        except (RuntimeError, ValueError) as e:
            raise LLMRequestFailedError(str(e))

    async def _handle_error(self, provider_name: str, key_info: KeyInfo, error: LLMError):
        if error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
            await self.key_manager.mark_as_banned(provider_name, key_info.key_string)
        elif error.error_type == LLMErrorType.RATE_LIMIT_ERROR:
            self.key_manager.mark_as_rate_limited(
                provider_name, key_info.key_string, error.retry_after_seconds or 60
            )

    def _parse_model_name(self, model_name: str) -> (str, str):
        parts = model_name.split('/', 1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid model name format: '{model_name}'. Expected 'provider/model_id'.")
        return parts[0], parts[1]
    
    def _create_failure_response(self, model_name: str, error: LLMError) -> LLMResponse:
        return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error)

class MockLLMService:
    """
    一个 LLMService 的模拟实现，用于调试。
    它不进行任何网络调用，而是立即返回一个可预测的假响应。
    """
    def __init__(self, *args, **kwargs):
        print("--- Hevno LLM Gateway is running in MOCK/DEBUG mode. No real API calls will be made. ---")

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        # 模拟一个非常短暂的延迟
        await asyncio.sleep(0.05)
        
        mock_content = f"[MOCK RESPONSE for {model_name}] - Prompt received: '{prompt[:50]}...'"
        
        return LLMResponse(
            status=LLMResponseStatus.SUCCESS,
            content=mock_content,
            model_name=model_name,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 15, "total_tokens": len(prompt.split()) + 15}
        )