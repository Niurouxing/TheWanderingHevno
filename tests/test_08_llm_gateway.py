# tests/test_08_llm_gateway.py

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# --- 从 LLM 模块中导入所有需要测试的类和模型 ---
from backend.llm.models import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError
)
from backend.llm.providers.gemini import GeminiProvider, google_exceptions
from backend.llm.manager import (
    CredentialManager, KeyPoolManager, KeyInfo, KeyStatus
)
from backend.llm.service import LLMService, ProviderRegistry

# ---------------------------------------------------------------------------
# Fixtures: 测试组件的“原材料”
# (这部分保持不变)
# ---------------------------------------------------------------------------

@pytest.fixture
def credential_manager() -> CredentialManager:
    return CredentialManager()

@pytest.fixture
def key_pool_manager(credential_manager: CredentialManager) -> KeyPoolManager:
    manager = KeyPoolManager(credential_manager)
    manager.register_provider("gemini", "GEMINI_API_KEYS")
    return manager

@pytest.fixture
def gemini_provider() -> GeminiProvider:
    return GeminiProvider()

@pytest.fixture
def provider_registry(gemini_provider: GeminiProvider) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("gemini", gemini_provider)
    return registry

@pytest.fixture
def llm_service(key_pool_manager: KeyPoolManager, provider_registry: ProviderRegistry) -> LLMService:
    return LLMService(key_manager=key_pool_manager, provider_registry=provider_registry, max_retries=2)

# ---------------------------------------------------------------------------
# Section 1: 密钥管理器单元测试 (manager.py)
# (这部分保持不变，但修复了 mark_as_banned 的 await 调用)
# ---------------------------------------------------------------------------

@pytest.mark.llm_gateway
class TestKeyPoolManager:
    def test_credential_manager_loads_keys(self, credential_manager: CredentialManager):
        gemini_keys = credential_manager.load_keys_from_env("GEMINI_API_KEYS")
        assert gemini_keys == ["test_key_1", "test_key_2", "test_key_3"]

    async def test_acquire_and_release_key(self, key_pool_manager: KeyPoolManager):
        async with key_pool_manager.acquire_key("gemini") as key_info:
            assert isinstance(key_info, KeyInfo)

    async def test_key_banning_reduces_concurrency(self, key_pool_manager: KeyPoolManager):
        pool = key_pool_manager.get_pool("gemini")
        initial_concurrency = pool._semaphore._value
        # 【修复】使用 await 调用异步方法
        await key_pool_manager.mark_as_banned("gemini", "test_key_1")
        assert pool._semaphore._value == initial_concurrency - 1
        banned_key_info = next(k for k in pool._keys if k.key_string == "test_key_1")
        assert not banned_key_info.is_available()

    async def test_rate_limiting_and_recovery(self, key_pool_manager: KeyPoolManager):
        pool = key_pool_manager.get_pool("gemini")
        pool.mark_as_rate_limited("test_key_2", duration_seconds=0.1)
        limited_key_info = next(k for k in pool._keys if k.key_string == "test_key_2")
        assert not limited_key_info.is_available()
        await asyncio.sleep(0.2)
        assert limited_key_info.is_available()


# ---------------------------------------------------------------------------
# Section 2: 提供商适配器单元测试 (providers/gemini.py)
# ---------------------------------------------------------------------------

@pytest.mark.llm_gateway
@patch('backend.llm.providers.gemini.genai.GenerativeModel')
class TestGeminiProvider:
    """
    对 GeminiProvider 的单元测试，完全模拟外部 API 调用。
    """

    async def test_generate_success(self, mock_genai_model: MagicMock, gemini_provider: GeminiProvider):
        """测试场景：API 调用成功。"""
        # --- Arrange ---
        # 1. 构造一个模拟的成功响应数据对象
        mock_response_data = MagicMock()
        mock_response_data.text = "Mocked successful response"
        usage_mock = MagicMock()
        usage_mock.prompt_token_count, usage_mock.candidates_token_count, usage_mock.total_token_count = 10, 20, 30
        mock_response_data.usage_metadata = usage_mock
        mock_response_data.parts = [MagicMock()] # 表示内容未被过滤
        
        # 2. 【关键】将 mock 模型的异步方法设置为一个返回上述数据的 AsyncMock
        mock_model_instance = mock_genai_model.return_value
        mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response_data)

        # --- Act ---
        response = await gemini_provider.generate(
            prompt="A test prompt", model_name="gemini-1.5-pro", api_key="fake_key"
        )

        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Mocked successful response"
        assert response.usage["total_tokens"] == 30
        mock_model_instance.generate_content_async.assert_awaited_once()

    async def test_generate_filtered(self, mock_genai_model: MagicMock, gemini_provider: GeminiProvider):
        """测试场景：API 调用因安全策略被阻止。"""
        # --- Arrange ---
        mock_response_data = MagicMock()
        mock_response_data.parts = [] # 空 parts 表示内容被过滤
        feedback_mock = MagicMock()
        feedback_mock.block_reason.name = "SAFETY"
        mock_response_data.prompt_feedback = feedback_mock
        
        mock_model_instance = mock_genai_model.return_value
        mock_model_instance.generate_content_async = AsyncMock(return_value=mock_response_data)

        # --- Act ---
        response = await gemini_provider.generate(
            prompt="A sensitive prompt", model_name="gemini-1.5-pro", api_key="fake_key"
        )

        # --- Assert ---
        assert response.status == LLMResponseStatus.FILTERED
        assert response.error_details.error_type == LLMErrorType.INVALID_REQUEST_ERROR
        assert "Request blocked due to SAFETY" in response.error_details.message
        mock_model_instance.generate_content_async.assert_awaited_once()

    def test_translate_errors(self, mock_genai_model: MagicMock, gemini_provider: GeminiProvider):
        """测试 `translate_error` 方法能否正确映射各种异常。"""
        # --- Act & Assert ---
        # 逐一测试每种错误映射
        auth_error = gemini_provider.translate_error(google_exceptions.PermissionDenied("auth failed"))
        assert auth_error.error_type == LLMErrorType.AUTHENTICATION_ERROR
        assert not auth_error.is_retryable

        rate_limit_error = gemini_provider.translate_error(google_exceptions.ResourceExhausted("rate limit"))
        assert rate_limit_error.error_type == LLMErrorType.RATE_LIMIT_ERROR
        assert not rate_limit_error.is_retryable

        server_error = gemini_provider.translate_error(google_exceptions.ServiceUnavailable("server down"))
        assert server_error.error_type == LLMErrorType.PROVIDER_ERROR
        assert server_error.is_retryable

# ---------------------------------------------------------------------------
# Section 3: 核心服务集成测试 (service.py)
# ---------------------------------------------------------------------------

@pytest.mark.llm_gateway
class TestLLMServiceIntegration:
    """
    对 LLMService 的集成测试，测试其重试和故障转移的核心逻辑。
    我们在这里使用一个 mock 的 provider，以便精确控制其行为。
    """

    @pytest.fixture
    def mock_gemini_provider(self) -> AsyncMock:
        """提供一个可被精确控制行为的 mock GeminiProvider。"""
        # 使用 autospec=True 可以确保 mock 的接口与原始类匹配
        return AsyncMock(spec=GeminiProvider)
        
    @pytest.fixture
    def llm_service_with_mock_provider(self, key_pool_manager: KeyPoolManager, mock_gemini_provider: AsyncMock) -> LLMService:
        """提供一个配置了 mock provider 的 LLMService 实例。"""
        registry = ProviderRegistry()
        registry.register("gemini", mock_gemini_provider)
        return LLMService(key_manager=key_pool_manager, provider_registry=registry, max_retries=2)

    async def test_request_success_on_first_try(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试快乐路径：第一次尝试即成功。"""
        # --- Arrange ---
        mock_gemini_provider.generate.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        # --- Act ---
        response = await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")

        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        mock_gemini_provider.generate.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试重试逻辑：第一次失败（可重试），第二次成功。"""
        # --- Arrange ---
        # 第一次调用抛出可重试异常，第二次调用返回成功响应
        mock_gemini_provider.generate.side_effect = [
            google_exceptions.ServiceUnavailable("Server temporary down"),
            LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")
        ]
        # 配置 translate_error 以正确识别该异常
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True
        )
        
        # --- Act ---
        response = await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        
        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Success after retry!"
        assert mock_gemini_provider.generate.call_count == 2
        mock_gemini_provider.translate_error.assert_called_once()

    async def test_failover_on_auth_error_and_succeed(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试故障转移逻辑：第一次认证失败，切换密钥后第二次成功。"""
        # --- Arrange ---
        mock_gemini_provider.generate.side_effect = [
            google_exceptions.PermissionDenied("Invalid Key"),
            LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success with new key!")
        ]
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.AUTHENTICATION_ERROR, message="Invalid Key", is_retryable=False
        )
        
        # --- Act ---
        response = await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")

        # --- Assert ---
        assert response.status == LLMResponseStatus.SUCCESS
        assert mock_gemini_provider.generate.call_count == 2
        
        # 验证两次调用使用了不同的密钥
        first_call_key = mock_gemini_provider.generate.call_args_list[0].kwargs['api_key']
        second_call_key = mock_gemini_provider.generate.call_args_list[1].kwargs['api_key']
        assert first_call_key != second_call_key

        # 验证第一个密钥已被禁用
        pool = llm_service_with_mock_provider.key_manager.get_pool("gemini")
        banned_key = next(k for k in pool._keys if k.key_string == first_call_key)
        assert banned_key.status == KeyStatus.BANNED

    async def test_final_failure_after_all_retries(self, llm_service_with_mock_provider: LLMService, mock_gemini_provider: AsyncMock):
        """测试最终失败路径：所有重试次数用尽。"""
        # --- Arrange ---
        # 所有调用都抛出同一个可重试异常
        mock_gemini_provider.generate.side_effect = google_exceptions.ServiceUnavailable("Server persistently down")
        mock_gemini_provider.translate_error.return_value = LLMError(
            error_type=LLMErrorType.PROVIDER_ERROR, message="Server down", is_retryable=True
        )
        
        # --- Act & Assert ---
        with pytest.raises(LLMRequestFailedError) as exc_info:
            await llm_service_with_mock_provider.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
        
        # 验证异常信息和调用次数
        max_retries = llm_service_with_mock_provider.max_retries
        assert f"failed after {max_retries} attempt(s)" in str(exc_info.value)
        assert exc_info.value.last_error.error_type == LLMErrorType.PROVIDER_ERROR
        assert mock_gemini_provider.generate.call_count == max_retries