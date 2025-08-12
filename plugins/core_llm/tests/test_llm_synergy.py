import pytest
import asyncio
import uuid  # <--- FIX: Added import for UUID generation
from unittest.mock import AsyncMock, patch, call, Mock
from typing import Tuple, Dict, Any, List

# From platform core
from backend.core.contracts import Container
from backend.core.utils import DotAccessibleDict

# From engine plugin
from plugins.core_engine.contracts import ExecutionContext, SharedContext, StateSnapshot

# From this plugin's contracts
from plugins.core_llm.contracts import (
    LLMResponse, LLMResponseStatus, LLMRequestFailedError, LLMServiceInterface
)
# From this plugin's implementation
from plugins.core_llm.manager import KeyPoolManager, KeyStatus
from plugins.core_llm.providers.gemini import GeminiProvider
from plugins.core_llm.providers.mock import MockProvider
from plugins.core_llm.runtime import LLMRuntime
from google.api_core import exceptions as google_exceptions

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


# --- Fixture for Unit/Integration Tests ---

@pytest.fixture
def unit_test_llm_service(test_engine_setup: Tuple[None, Container, None], monkeypatch) -> Tuple[LLMServiceInterface, KeyPoolManager]:
    monkeypatch.setenv("GEMINI_API_KEYS", "unit_test_key_1,unit_test_key_2")
    _, container, _ = test_engine_setup
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")
    if hasattr(key_manager, '_pools'):
        key_manager._pools.clear() 
    key_manager.register_provider("gemini", "GEMINI_API_KEYS")
    service: LLMServiceInterface = container.resolve("llm_service")
    return service, key_manager

# --- Fixture for E2E Tests ---

@pytest.fixture
def e2e_llm_service(test_engine_setup: Tuple[None, Container, None]) -> LLMServiceInterface:
    _, container, _ = test_engine_setup
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")
    if hasattr(key_manager, '_pools'):
        key_manager._pools.clear()
        key_manager.register_provider("gemini", "GEMINI_API_KEYS")
    service: LLMServiceInterface = container.resolve("llm_service")
    return service

# --- Test Suite for LLMService (The Gateway) ---

class TestLLMServiceLogic:
    """Tests the internal logic of the LLMService gateway, like retry and key switching."""

    async def test_request_success_on_first_try(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        test_messages = [{"role": "user", "content": "Hello"}]
        
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = success_response
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", messages=test_messages)
            assert response.status == LLMResponseStatus.SUCCESS
            mock_generate.assert_awaited_once_with(messages=test_messages, model_name='gemini-1.5-pro', api_key='unit_test_key_1')

    async def test_retry_on_provider_error_and_succeed(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        retryable_exception = google_exceptions.ServiceUnavailable("503 Service Unavailable")
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")
        test_messages = [{"role": "user", "content": "Hello"}]

        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = [retryable_exception, success_response]
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", messages=test_messages)
            assert response.status == LLMResponseStatus.SUCCESS
            assert mock_generate.call_count == 2

    async def test_final_failure_after_all_retries(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        # ... (rest of the test is unchanged) ...
        test_messages = [{"role": "user", "content": "Hello"}]
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = google_exceptions.ServiceUnavailable("503 Service Unavailable")
            with pytest.raises(LLMRequestFailedError):
                await llm_service.request(model_name="gemini/gemini-1.5-pro", messages=test_messages)
            assert mock_generate.call_count == 3

    async def test_key_is_banned_on_authentication_error_and_switches(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, key_manager = unit_test_llm_service
        # ... (rest of the test is unchanged) ...
        test_messages = [{"role": "user", "content": "Request that will switch keys"}]
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = [google_exceptions.PermissionDenied("401"), LLMResponse(status=LLMResponseStatus.SUCCESS, content="OK")]
            await llm_service.request(model_name="gemini/gemini-1.5-pro", messages=test_messages)
            pool = key_manager.get_pool("gemini")
            assert pool.get_key_by_string("unit_test_key_1").status == KeyStatus.BANNED

# --- Test Suite for Mock Provider ---
class TestLLMServiceWithMockProvider:
    # ... (these tests are unchanged and should still pass) ...
    async def test_mock_provider_request_succeeds(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        test_messages = [{"role": "user", "content": "Test Prompt"}]
        with patch.object(MockProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Verified Mock Call")
            response = await llm_service.request(model_name="mock/any-model", messages=test_messages)
            assert response.status == LLMResponseStatus.SUCCESS

    async def test_mock_provider_does_not_use_key_manager(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, key_manager = unit_test_llm_service
        test_messages = [{"role": "user", "content": "Test"}]
        with patch.object(key_manager, 'acquire_key', new_callable=AsyncMock) as mock_acquire_key:
            await llm_service.request(model_name="mock/any-model", messages=test_messages)
            mock_acquire_key.assert_not_called()

# --- NEW: Test Suite for LLMRuntime (The "List Expansion" Logic) ---

@pytest.fixture
def mock_exec_context(test_engine_setup) -> ExecutionContext:
    """Provides a mocked ExecutionContext for runtime tests."""
    _, container, hook_manager = test_engine_setup
    
    mock_llm_service = AsyncMock(spec=LLMServiceInterface)
    mock_macro_service = container.resolve("macro_evaluation_service")
    
    # --- FIX: Use patch.object for safe, isolated mocking ---
    def resolve_side_effect(name):
        if name == "llm_service":
            return mock_llm_service
        return container.__class__.resolve(container, name) # Call original method

    with patch.object(container, 'resolve', side_effect=resolve_side_effect):
        shared_context = SharedContext(
            definition_state={},
            lore_state={},
            moment_state={},
            session_info={},
            global_write_lock=asyncio.Lock(),
            services=DotAccessibleDict({
                'llm_service': mock_llm_service,
                'macro_evaluation_service': mock_macro_service
            })
        )
        
        yield ExecutionContext(
            shared=shared_context,
            # --- FIX: Use a valid UUID ---
            initial_snapshot=StateSnapshot(sandbox_id=uuid.uuid4(), moment={}),
            hook_manager=hook_manager,
            node_states={},
            run_vars={}
        )
    # The patch is automatically removed upon exiting the 'with' block


class TestLLMRuntimeSynergy:
    """Tests the core synergy logic of the `llm.default` runtime."""

    async def test_contents_with_message_part_and_injection(self, mock_exec_context: ExecutionContext):
        runtime = LLMRuntime()
        mock_llm_service = mock_exec_context.shared.services.llm_service
        mock_llm_service.request.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Final Output")

        mock_exec_context.node_states['get_history'] = {
            "output": [
                {"role": "user", "content": "Hello from history"},
                {"role": "model", "content": "Hi there from history"}
            ]
        }
        
        config = {
            "model": "gemini/test-model",
            "contents": [
                {"type": "MESSAGE_PART", "role": "system", "content": "You are a test assistant."},
                {"type": "INJECT_MESSAGES", "source": "{{ nodes.get_history.output }}"},
                {"type": "MESSAGE_PART", "role": "user", "content": "This is the final user message."}
            ]
        }
        
        await runtime.execute(config, mock_exec_context)
        
        expected_messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Hello from history"},
            {"role": "model", "content": "Hi there from history"},
            {"role": "user", "content": "This is the final user message."}
        ]
        
        mock_llm_service.request.assert_awaited_once_with(
            model_name="gemini/test-model", messages=expected_messages
        )

    async def test_is_enabled_switch(self, mock_exec_context: ExecutionContext):
        # ... (this test is unchanged and should now pass) ...
        runtime = LLMRuntime()
        mock_llm_service = mock_exec_context.shared.services.llm_service
        mock_llm_service.request.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="OK")
        mock_exec_context.node_states['get_history'] = {"output": [{"role": "user", "content": "This should be ignored."}]}
        
        config = {
            "model": "gemini/test-model",
            "contents": [
                {"type": "MESSAGE_PART", "role": "system", "content": "You are a test assistant."},
                {"type": "INJECT_MESSAGES", "source": "{{ nodes.get_history.output }}", "is_enabled": False},
                {"type": "MESSAGE_PART", "role": "user", "content": "This should be ignored.", "is_enabled": False},
                {"type": "MESSAGE_PART", "role": "user", "content": "This is the only user message."}
            ]
        }
        
        await runtime.execute(config, mock_exec_context)
        
        expected_messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "This is the only user message."}
        ]
        
        mock_llm_service.request.assert_awaited_once_with(
            model_name="gemini/test-model", messages=expected_messages
        )

# --- Test Suite for E2E ---
class TestLLMEndToEnd:
    @pytest.mark.e2e
    async def test_real_gemini_api_request(self, e2e_llm_service: LLMServiceInterface):
        # This test should now receive the REAL service due to the isolated mocking fix
        llm_service = e2e_llm_service
        model_name = "gemini/gemini-1.5-flash"
        messages = [{"role": "user", "content": "What color is the sky? Answer briefly in English."}]

        try:
            response = await llm_service.request(model_name=model_name, messages=messages)
        except LLMRequestFailedError as e:
            pytest.fail(f"Real API request failed unexpectedly: {e}")
        
        assert response is not None
        assert response.status == LLMResponseStatus.SUCCESS, f"API request failed: {response.error_details.message if response.error_details else 'No details'}"
        assert response.content is not None and len(response.content.strip()) > 0
        print(f"\nReal Gemini API Response: '{response.content.strip()}'")
        assert response.usage is not None and response.usage["total_tokens"] > 0