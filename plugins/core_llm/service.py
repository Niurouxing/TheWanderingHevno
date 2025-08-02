# plugins/core_llm/service.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Optional, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    RetryCallState, # 导入 RetryCallState
)

# --- 从本插件内部导入组件 ---
from .manager import KeyPoolManager, KeyInfo
from .models import (
    LLMResponse,
    LLMError,
    LLMErrorType,
    LLMResponseStatus,
    LLMRequestFailedError,
)
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


def is_retryable_llm_error(retry_state: RetryCallState) -> bool:
    """
    一个 tenacity 重试条件函数。
    【终极修复】它接收一个 RetryCallState 对象，我们需要从中提取真正的异常。
    """
    # 从 retry_state 中获取导致失败的异常
    exception = retry_state.outcome.exception()

    if not exception:
        return False # 如果没有异常，就不重试

    return (
        isinstance(exception, LLMRequestFailedError) and
        exception.last_error is not None and
        exception.last_error.is_retryable
    )


class LLMService:
    """
    LLM 网关的核心服务，负责协调所有组件并执行请求。
    实现了带有密钥轮换、状态管理和指数退避的健壮重试逻辑。
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
        self.last_known_error: Optional[LLMError] = None

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        向指定的 LLM 发起请求，并处理重试逻辑。
        """
        self.last_known_error = None
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

        def log_before_sleep(retry_state: RetryCallState):
            """在 tenacity 每次重试前调用的日志记录函数。"""
            exc = retry_state.outcome.exception()
            if exc and isinstance(exc, LLMRequestFailedError) and exc.last_error:
                error_type = exc.last_error.error_type.value
            else:
                error_type = "unknown"
            
            logger.warning(
                f"LLM request for {model_name} failed with a retryable error ({error_type}). "
                f"Waiting {retry_state.next_action.sleep:.2f}s before attempt {retry_state.attempt_number + 1}."
            )
        
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=is_retryable_llm_error,
            reraise=True,
            before_sleep=log_before_sleep
        )

        wrapped_attempt = retry_decorator(self._attempt_request)
        try:
            return await wrapped_attempt(provider_name, actual_model_name, prompt, **kwargs)
        
        except LLMRequestFailedError as e:
            final_message = (
                f"LLM request for model '{model_name}' failed permanently after {self.max_retries} attempt(s)."
            )
            # exc_info=False 因为我们正在从原始异常链中引发一个新的、更清晰的异常
            logger.error(final_message, exc_info=False)
            raise LLMRequestFailedError(final_message, last_error=self.last_known_error) from e
        
        except Exception as e:
            logger.critical(f"An unexpected non-LLM error occurred in LLMService: {e}", exc_info=True)
            raise

    async def _attempt_request(
        self,
        provider_name: str,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """
        执行单次 LLM 请求尝试。
        """
        provider = self.provider_registry.get(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found.")

        try:
            async with self.key_manager.acquire_key(provider_name) as key_info:
                response = await provider.generate(
                    prompt=prompt, model_name=model_name, api_key=key_info.key_string, **kwargs
                )
                
                if response.status in [LLMResponseStatus.ERROR, LLMResponseStatus.FILTERED] and response.error_details:
                    self.last_known_error = response.error_details
                    await self._handle_error(provider_name, key_info, response.error_details)
                    
                    if response.error_details.is_retryable:
                        raise LLMRequestFailedError("Provider returned a retryable error response.", last_error=response.error_details)

                return response
        
        except Exception as e:
            if isinstance(e, LLMRequestFailedError):
                raise e

            llm_error = provider.translate_error(e)
            self.last_known_error = llm_error
            
            error_message = f"Request attempt failed due to an exception: {llm_error.message}"
            raise LLMRequestFailedError(error_message, last_error=llm_error) from e

    async def _handle_error(self, provider_name: str, key_info: KeyInfo, error: LLMError):
        """根据错误类型更新密钥池中密钥的状态。"""
        if error.error_type == LLMErrorType.AUTHENTICATION_ERROR:
            logger.warning(f"Authentication error with key for '{provider_name}'. Banning key.")
            await self.key_manager.mark_as_banned(provider_name, key_info.key_string)
        elif error.error_type == LLMErrorType.RATE_LIMIT_ERROR:
            cooldown = error.retry_after_seconds or 60
            logger.info(f"Rate limit hit for key on '{provider_name}'. Cooling down for {cooldown}s.")
            self.key_manager.mark_as_rate_limited(provider_name, key_info.key_string, cooldown)

    def _parse_model_name(self, model_name: str) -> tuple[str, str]:
        """将 'provider/model_id' 格式的字符串解析为元组。"""
        parts = model_name.split('/', 1)
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid model name format: '{model_name}'. Expected 'provider/model_id'.")
        return parts[0], parts[1]
    
    def _create_failure_response(self, model_name: str, error: LLMError) -> LLMResponse:
        """创建一个标准的错误响应对象。"""
        return LLMResponse(status=LLMResponseStatus.ERROR, model_name=model_name, error_details=error)


class MockLLMService:
    """
    一个 LLMService 的模拟实现，用于调试和测试。
    它不进行任何网络调用，而是立即返回一个可预测的假响应。
    """
    def __init__(self, *args, **kwargs):
        logger.info("--- MockLLMService Initialized: Real LLM calls are disabled. ---")

    async def request(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        await asyncio.sleep(0.05)
        mock_content = f"[MOCK RESPONSE for {model_name}] - Prompt received: '{prompt[:150]}...'"
        
        return LLMResponse(
            status=LLMResponseStatus.SUCCESS,
            content=mock_content,
            model_name=model_name,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 15, "total_tokens": len(prompt.split()) + 15}
        )