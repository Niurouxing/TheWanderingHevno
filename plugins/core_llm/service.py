# plugins/core_llm/service.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    RetryCallState,
)

from .manager import KeyPoolManager, KeyInfo
from .registry import ProviderRegistry
from .contracts import (
    LLMServiceInterface,
    LLMResponse,
    LLMError,
    LLMErrorType,
    LLMResponseStatus,
    LLMRequestFailedError,
)

logger = logging.getLogger(__name__)

def is_retryable_llm_error(retry_state: RetryCallState) -> bool:
    """Tenacity 重试条件：只在错误是可重试类型时才重试。"""
    exception = retry_state.outcome.exception()
    if not exception:
        return False
    return (
        isinstance(exception, LLMRequestFailedError) and
        exception.last_error is not None and
        exception.last_error.is_retryable
    )

class LLMService(LLMServiceInterface):
    def __init__(
        self,
        key_manager: KeyPoolManager,
        provider_registry: ProviderRegistry,
        max_retries: int = 3
    ):
        self.key_manager = key_manager
        self.provider_registry = provider_registry
        self.max_retries = max_retries
        self.last_known_error: Optional[LLMError] = None

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        【已重构】
        向指定的 LLM 发起请求。
        此方法现在包含一个外层循环，用于在密钥认证失败时自动切换到下一个可用密钥。
        """
        self.last_known_error = None
        try:
            provider_name, actual_model_name = self._parse_model_name(model_name)
        except ValueError as e:
            return self._create_failure_response(model_name, LLMError(LLMErrorType.INVALID_REQUEST_ERROR, str(e), False))

        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found.")
            
        # 如果提供商不需要密钥，直接调用并返回
        if not provider.requires_api_key():
            return await self._attempt_request_with_key(provider_name, actual_model_name, prompt, None, **kwargs)

        key_pool = self.key_manager.get_pool(provider_name)
        if not key_pool:
             raise ValueError(f"No key pool registered for provider '{provider_name}'.")

        # 外层循环：遍历所有密钥，实现密钥切换
        # 我们使用密钥池中密钥的总数作为尝试上限
        num_keys = key_pool.get_key_count()
        for attempt in range(num_keys):
            try:
                # 每次循环都尝试获取一个可用的密钥
                async with self.key_manager.acquire_key(provider_name) as key_info:
                    # 使用此密钥进行请求（包含内部的 tenacity 重试）
                    return await self._attempt_request_with_key(
                        provider_name, actual_model_name, prompt, key_info, **kwargs
                    )
            except LLMRequestFailedError as e:
                # 检查失败的根本原因
                if e.last_error and e.last_error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
                    # 如果是认证失败，记录日志并继续外层循环以尝试下一个密钥
                    logger.warning(
                        f"Authentication failed for key ending in '...{key_info.key_string[-4:]}'. "
                        f"Trying next available key... ({attempt + 1}/{num_keys} attempts)"
                    )
                    continue # 继续 for 循环
                else:
                    # 如果是其他类型的永久性错误，则直接抛出
                    raise
        
        # 如果循环完成仍未成功，说明所有密钥都已尝试并失败
        final_message = f"All {num_keys} API keys for provider '{provider_name}' failed."
        raise LLMRequestFailedError(final_message, last_error=self.last_known_error)

    @retry(
        stop=stop_after_attempt(3), # 内层重试次数
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_llm_error,
        reraise=True
    )
    async def _attempt_request_with_key(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        key_info: Optional[KeyInfo],
        **kwargs
    ) -> LLMResponse:
        """
        【新】使用一个【特定】的密钥执行单次 LLM 请求尝试。
        此方法被 tenacity 装饰器包裹，用于处理瞬时错误。
        """
        provider = self.provider_registry.get(provider_name)
        api_key_str = key_info.key_string if key_info else ""

        try:
            response = await provider.generate(
                prompt=prompt, model_name=model_name, api_key=api_key_str, **kwargs
            )
            
            if response.status in [LLMResponseStatus.ERROR, LLMResponseStatus.FILTERED] and response.error_details:
                self.last_known_error = response.error_details
                if key_info:
                    await self._handle_error(provider_name, key_info, response.error_details)
                
                # 如果错误是可重试的，抛出异常让 tenacity 捕获
                if response.error_details.is_retryable:
                    raise LLMRequestFailedError("Provider returned a retryable error.", last_error=response.error_details)
            
            return response
        
        except Exception as e:
            if isinstance(e, LLMRequestFailedError):
                raise

            llm_error = provider.translate_error(e)
            self.last_known_error = llm_error
            if key_info:
                await self._handle_error(provider_name, key_info, llm_error)

            raise LLMRequestFailedError(f"Request failed with key: {llm_error.message}", last_error=llm_error) from e

    async def _handle_error(self, provider_name: str, key_info: KeyInfo, error: LLMError):
        if error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
            logger.warning(f"Banning key for '{provider_name}' due to authentication error.")
            await self.key_manager.mark_as_banned(provider_name, key_info.key_string)
        elif error.error_type == LLMErrorType.RATE_LIMIT_ERROR:
            cooldown = error.retry_after_seconds or 60
            logger.info(f"Cooling down key for '{provider_name}' for {cooldown}s due to rate limit.")
            self.key_manager.mark_as_rate_limited(provider_name, key_info.key_string, cooldown)

    def _parse_model_name(self, model_name: str) -> tuple[str, str]:
        parts = model_name.split('/', 1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid model name format: '{model_name}'. Expected 'provider/model_id'.")
        return parts[0], parts[1]
    
    def _create_failure_response(self, model_name: str, error: LLMError) -> LLMResponse:
        return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error)