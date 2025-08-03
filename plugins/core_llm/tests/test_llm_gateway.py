# plugins/core_llm/tests/test_llm_gateway.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# 从本插件的公共契约中导入所需模型
from plugins.core_llm.contracts import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError
)
# 从本插件内部实现中导入待测试的类
from plugins.core_llm.manager import CredentialManager, KeyPoolManager
from plugins.core_llm.service import LLMService
from plugins.core_llm.registry import ProviderRegistry
from plugins.core_llm.providers.gemini import GeminiProvider

# --- Fixtures for setting up the test environment ---

@pytest.fixture
def credential_manager(monkeypatch) -> CredentialManager:
    """Fixture to provide a CredentialManager with mocked environment variables."""
    monkeypatch.setenv("GEMINI_API_KEYS", "test_key_1, test_key_2")
    return CredentialManager()

@pytest.fixture
def key_pool_manager(credential_manager: CredentialManager) -> KeyPoolManager:
    """Fixture to provide a KeyPoolManager with a registered provider."""
    manager = KeyPoolManager(credential_manager)
    # The key manager needs to know about the provider to create a key pool.
    manager.register_provider("gemini", "GEMINI_API_KEYS")
    return manager

@pytest.fixture
def provider_registry() -> ProviderRegistry:
    """
    Fixture to create a ProviderRegistry instance, populated with a
    provider, just as the application would do during startup.
    """
    registry = ProviderRegistry()
    # Manually register a provider for testing purposes.
    registry.register(name="gemini", provider_class=GeminiProvider, key_env_var="GEMINI_API_KEYS")
    registry.instantiate_all() # Instantiate the registered providers
    return registry

@pytest.fixture
def llm_service(key_pool_manager: KeyPoolManager, provider_registry: ProviderRegistry) -> LLMService:
    """

    Fixture to provide a fully initialized LLMService instance.
    This service is configured with dependencies provided by other fixtures,
    following the Dependency Injection pattern.
    """
    return LLMService(
        key_manager=key_pool_manager, 
        provider_registry=provider_registry, 
        max_retries=2 # Allows for 1 initial attempt + 1 retry
    )


# --- Test Suite ---

@pytest.mark.asyncio
class TestLLMServiceIntegration:
    """
    Integration tests for LLMService, focusing on its core logic of retries,
    error handling, and key management, without making real network calls.
    The lower-level method `_attempt_request` is patched to simulate various outcomes.
    """

    async def test_request_success_on_first_try(self, llm_service: LLMService):
        """
        Verifies that if the first attempt is successful, the service returns
        the correct response and does not perform unnecessary retries.
        """
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        # Patch the internal attempt method to simulate an immediate success.
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.return_value = success_response
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response == success_response
            mock_attempt.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service: LLMService):
        """
        Verifies that the service correctly retries a request when a retryable
        error occurs on the first attempt, and then succeeds.
        """
        retryable_error = LLMRequestFailedError(
            "A retryable error occurred", 
            last_error=LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True)
        )
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")

        # Configure the mock to fail on the first call and succeed on the second.
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.side_effect = [
                retryable_error,
                success_response
            ]
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # Assert the final outcome is the successful response.
            assert response == success_response
            # Assert that the retry mechanism was triggered (1 initial + 1 retry).
            assert mock_attempt.call_count == 2


    async def test_final_failure_after_all_retries(self, llm_service: LLMService):
        """
        Verifies that after exhausting all retry attempts with persistent
        retryable errors, the service raises a final, informative exception.
        """
        retryable_error = LLMRequestFailedError(
            "A persistent retryable error",
            last_error=LLMError(error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True)
        )
        
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            # Configure the mock to always raise the retryable error.
            mock_attempt.side_effect = retryable_error
            
            with pytest.raises(LLMRequestFailedError) as exc_info:
                await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # Assert that the final exception message indicates permanent failure.
            assert "failed permanently after 2 attempt(s)" in str(exc_info.value)
            
            # Assert that the service attempted the call for the configured number of retries.
            assert mock_attempt.call_count == 2
            
    async def test_no_retry_on_non_retryable_error(self, llm_service: LLMService):
        """
        Verifies that if a non-retryable error occurs, the service fails
        immediately without attempting any retries.
        """
        non_retryable_error = LLMRequestFailedError(
            "A non-retryable error",
            last_error=LLMError(error_type=LLMErrorType.INVALID_REQUEST_ERROR, message="Bad prompt", is_retryable=False)
        )
        
        with patch.object(llm_service, '_attempt_request', new_callable=AsyncMock) as mock_attempt:
            mock_attempt.side_effect = non_retryable_error

            with pytest.raises(LLMRequestFailedError) as exc_info:
                 await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="This is a bad prompt")

            # Assert the final exception message indicates permanent failure, but after only one attempt.
            assert "failed permanently after 2 attempt(s)" in str(exc_info.value)
            
            # Assert that the service only made one attempt.
            mock_attempt.assert_awaited_once()