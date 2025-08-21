# plugins/core_llm/service.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Optional, Any, List

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
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> LLMResponse:
        """
        向指定的 LLM 发起请求，现在支持自动路由和故障转移。
        它会首先尝试模型的原生提供商，如果失败，则会依次尝试所有
        通过别名声明可以提供该模型的自定义提供商。
        """
        self.last_known_error = None
        
        # 1. 确定所有潜在的候选提供商
        try:
            native_provider_name, _ = self._parse_model_name(model_name)
        except ValueError as e:
            return self._create_failure_response(model_name, LLMError(LLMErrorType.INVALID_REQUEST_ERROR, str(e), False))

        # 从能力图谱中获取所有代理/别名提供商
        proxy_providers = self.provider_registry.get_providers_for_model(model_name)
        
        # 构建最终的尝试列表，原生提供商优先，然后去重
        candidate_providers = [native_provider_name]
        for p in proxy_providers:
            if p not in candidate_providers:
                candidate_providers.append(p)
        
        logger.info(f"Request for model '{model_name}'. Candidate providers in order: {candidate_providers}")

        # 2. 依次尝试每个候选提供商
        last_exception = None
        for provider_name in candidate_providers:
            try:
                logger.debug(f"Attempting model '{model_name}' with provider '{provider_name}'...")
                # 尝试使用这个提供商（及其所有密钥）来完成请求
                response = await self._attempt_request_with_provider(
                    provider_name, model_name, messages, **kwargs
                )
                
                # 只要不抛出异常，就说明请求成功或被 provider 优雅处理了
                logger.info(f"Successfully handled request for '{model_name}' using provider '{provider_name}'.")
                return response

            except LLMRequestFailedError as e:
                logger.warning(
                    f"Provider '{provider_name}' failed to handle request for '{model_name}'. Reason: {e}. "
                    "Trying next available provider..."
                )
                last_exception = e
                self.last_known_error = e.last_error
                continue # 继续下一个 provider
        
        # 3. 如果所有提供商都失败了
        final_message = f"All candidate providers ({candidate_providers}) failed for model '{model_name}'."
        if last_exception:
            raise LLMRequestFailedError(final_message, last_error=last_exception.last_error) from last_exception
        else:
            # 这种情况理论上不应该发生，但作为保险
            raise LLMRequestFailedError(final_message, last_error=self.last_known_error)


    async def _attempt_request_with_provider(
        self,
        provider_name: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> LLMResponse:
        """
        
        尝试使用一个【特定】的提供商（及其所有可用密钥）来完成请求。
        """
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise LLMRequestFailedError(f"Provider '{provider_name}' not found in registry.")
            
        # 如果提供商不需要密钥，直接调用并返回
        if not provider.requires_api_key():
            return await self._attempt_request_with_key(provider_name, model_name, messages, None, **kwargs)

        key_pool = self.key_manager.get_pool(provider_name)
        if not key_pool:
             raise LLMRequestFailedError(f"No key pool registered for provider '{provider_name}'.")

        num_keys = key_pool.get_key_count()
        if num_keys == 0:
            raise LLMRequestFailedError(f"No API keys configured for provider '{provider_name}'.")

        # 内层循环：遍历该提供商的所有密钥
        for attempt in range(num_keys):
            try:
                async with self.key_manager.acquire_key(provider_name) as key_info:
                    return await self._attempt_request_with_key(
                        provider_name, model_name, messages, key_info, **kwargs
                    )
            except LLMRequestFailedError as e:
                if e.last_error and e.last_error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
                    logger.warning(
                        f"Authentication failed for key of '{provider_name}' ending '...{key_info.key_string[-4:]}'. "
                        f"Trying next key... ({attempt + 1}/{num_keys} attempts for this provider)"
                    )
                    continue
                else:
                    raise # 其他类型的永久性错误，直接终止对该提供商的尝试
        
        # 如果循环完成，说明该提供商的所有密钥都因认证失败
        raise LLMRequestFailedError(
            f"All {num_keys} API keys for provider '{provider_name}' failed authentication.", 
            last_error=self.last_known_error
        )


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_llm_error,
        reraise=True
    )
    async def _attempt_request_with_key(
        self,
        provider_name: str,
        model_name: str,
        messages: List[Dict[str, Any]],
        key_info: Optional[KeyInfo],
        **kwargs
    ) -> LLMResponse:
        """
        使用一个【特定】的密钥执行单次 LLM 请求尝试。
        """
        provider = self.provider_registry.get(provider_name)
        api_key_str = key_info.key_string if key_info else ""
        
        # 【BUG 修复 1/2】
        # 总是解析出不带前缀的模型名称，并将其传递给 provider.generate
        _, actual_model_name = self._parse_model_name(model_name)

        try:
            response = await provider.generate(
                messages=messages, 
                model_name=actual_model_name, # <-- 使用修正后的变量
                api_key=api_key_str, 
                **kwargs
            )
            
            if response.status in [LLMResponseStatus.ERROR, LLMResponseStatus.FILTERED] and response.error_details:
                self.last_known_error = response.error_details
                if key_info:
                    await self._handle_error(provider_name, key_info, response.error_details)
                
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