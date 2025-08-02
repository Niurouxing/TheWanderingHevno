# plugins/core_llm/tests/test_llm_gateway.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# 从本插件内部导入所有需要测试的类和模型
from plugins.core_llm.models import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError
)
from plugins.core_llm.manager import CredentialManager, KeyPoolManager
from plugins.core_llm.service import LLMService
from plugins.core_llm.registry import ProviderRegistry, provider_registry as global_provider_registry

# 为了测试的隔离性，我们清除全局注册表
@pytest.fixture(autouse=True)
def isolated_provider_registry():
    backup_providers = global_provider_registry._providers.copy()
    backup_info = global_provider_registry._provider_info.copy()
    global_provider_registry._providers.clear()
    global_provider_registry._provider_info.clear()
    yield
    global_provider_registry._providers = backup_providers
    global_provider_registry._provider_info = backup_info

@pytest.fixture
def credential_manager(monkeypatch) -> CredentialManager:
    monkeypatch.setenv("GEMINI_API_KEYS", "test_key_1, test_key_2")
    return CredentialManager()

@pytest.fixture
def key_pool_manager(credential_manager: CredentialManager) -> KeyPoolManager:
    manager = KeyPoolManager(credential_manager)
    manager.register_provider("gemini", "GEMINI_API_KEYS")
    return manager

# 【修复】这个 fixture 现在只创建 LLMService，不再 mock provider
# 因为我们将在测试函数内部 patch 更高层次的方法
@pytest.fixture
def llm_service(key_pool_manager: KeyPoolManager) -> LLMService:
    # 注册一个空的 provider registry，因为我们不会真的调用它
    return LLMService(
        key_manager=key_pool_manager, 
        provider_registry=ProviderRegistry(), 
        max_retries=2 # 1 initial + 1 retry = 2 total attempts
    )

@pytest.mark.asyncio
class TestLLMServiceIntegration:
    """对 LLMService 的集成测试，测试其重试和故障转移的核心逻辑。"""

    async def test_request_success_on_first_try(self, llm_service: LLMService):
        """测试在第一次尝试就成功时，方法能正确返回。"""
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        # 使用 patch 直接模拟 _attempt_request 的行为
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.return_value = success_response
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response == success_response
            mock_attempt.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service: LLMService):
        """
        【修复后】测试当 _attempt_request 第一次失败、第二次成功时，tenacity 是否正确重试。
        """
        retryable_error = LLMRequestFailedError(
            "A retryable error occurred", 
            last_error=LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True)
        )
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")

        # 直接 patch _attempt_request，并让它按顺序产生效果
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.side_effect = [
                retryable_error,
                success_response
            ]
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # 验证最终结果是成功的响应
            assert response == success_response
            # 验证 _attempt_request 被调用了两次（1次初始 + 1次重试）
            assert mock_attempt.call_count == 2


    async def test_final_failure_after_all_retries(self, llm_service: LLMService):
        """
        【修复后】测试当 _attempt_request 总是失败时，是否在耗尽重试次数后抛出最终异常。
        """
        retryable_error = LLMRequestFailedError(
            "A persistent retryable error",
            last_error=LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True)
        )
        
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            # 让 mock 的方法总是抛出可重试的异常
            mock_attempt.side_effect = retryable_error
            
            with pytest.raises(LLMRequestFailedError) as exc_info:
                await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # 验证最终抛出的异常包含了总结性的信息
            assert "failed permanently after 2 attempt(s)" in str(exc_info.value)
            
            # 验证 _attempt_request 被调用了两次（1次初始 + 1次重试）
            assert mock_attempt.call_count == 2