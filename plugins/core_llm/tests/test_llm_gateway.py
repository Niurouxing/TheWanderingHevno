# plugins/core_llm/tests/test_llm_gateway.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# 从本插件内部导入所有需要测试的类和模型
from plugins.core_llm.models import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError
)
from plugins.core_llm.providers.gemini import GeminiProvider, google_exceptions
from plugins.core_llm.manager import CredentialManager, KeyPoolManager, KeyInfo, KeyStatus
from plugins.core_llm.service import LLMService
from plugins.core_llm.registry import ProviderRegistry, provider_registry as global_provider_registry

# 为了测试的隔离性，我们清除全局注册表
@pytest.fixture(autouse=True)
def isolated_provider_registry():
    backup = global_provider_registry._provider_info.copy()
    global_provider_registry._provider_info.clear()
    yield
    global_provider_registry._provider_info = backup

@pytest.fixture
def credential_manager(monkeypatch) -> CredentialManager:
    # 使用 monkeypatch 来模拟环境变量
    monkeypatch.setenv("GEMINI_API_KEYS", "test_key_1, test_key_2, test_key_3")
    return CredentialManager()

@pytest.fixture
def key_pool_manager(credential_manager: CredentialManager) -> KeyPoolManager:
    manager = KeyPoolManager(credential_manager)
    manager.register_provider("gemini", "GEMINI_API_KEYS")
    return manager

@pytest.fixture
def llm_service(key_pool_manager: KeyPoolManager, mock_gemini_provider) -> LLMService:
    # 使用一个注入了 Mock Provider 的 LLMService
    registry = ProviderRegistry()
    registry._providers["gemini"] = mock_gemini_provider # 直接注入 mock 实例
    return LLMService(key_manager=key_pool_manager, provider_registry=registry, max_retries=2)

@pytest.fixture
def mock_gemini_provider() -> AsyncMock:
    return AsyncMock(spec=GeminiProvider)

@pytest.mark.asyncio
class TestLLMServiceIntegration:
    """对 LLMService 的集成测试，测试其重试和故障转移的核心逻辑。"""

    async def test_request_success_on_first_try(self, llm_service: LLMService, mock_gemini_provider: AsyncMock):
        mock_gemini_provider.generate.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        assert response.status == LLMResponseStatus.SUCCESS
        mock_gemini_provider.generate.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service: LLMService, mock_gemini_provider: AsyncMock):
        mock_gemini_provider.generate.side_effect = [
            google_exceptions.ServiceUnavailable("Server temporary down"),
            LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")
        ]
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True
        )
        response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        assert response.status == LLMResponseStatus.SUCCESS
        assert mock_gemini_provider.generate.call_count == 2

    async def test_final_failure_after_all_retries(self, llm_service: LLMService, mock_gemini_provider: AsyncMock):
        mock_gemini_provider.generate.side_effect = google_exceptions.ServiceUnavailable("Server persistently down")
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True
        )
        with pytest.raises(LLMRequestFailedError) as exc_info:
            await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        assert f"failed permanently after 2 attempt(s)" in str(exc_info.value)
        assert mock_gemini_provider.generate.call_count == 2