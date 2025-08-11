import pytest
from unittest.mock import AsyncMock, patch, call
from typing import Tuple

# 从平台核心导入接口
from backend.core.contracts import Container

# 从本插件的公共契约中导入所需模型
from plugins.core_llm.contracts import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError, LLMServiceInterface
)
# 从本插件内部实现中导入待测试的类
from plugins.core_llm.manager import KeyPoolManager, KeyStatus
from plugins.core_llm.providers.gemini import GeminiProvider
from plugins.core_llm.providers.mock import MockProvider
from google.api_core import exceptions as google_exceptions

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


# --- Fixture for Unit/Integration Tests ---

@pytest.fixture
def unit_test_llm_service(test_engine_setup: Tuple[None, Container, None], monkeypatch) -> Tuple[LLMServiceInterface, KeyPoolManager]:
    """
    【单元测试专用 Fixture】
    为单元/集成测试提供一个配置了【模拟】API密钥的 LLMService。
    """
    # 1. 使用 monkeypatch 设置模拟的环境变量
    monkeypatch.setenv("GEMINI_API_KEYS", "unit_test_key_1,unit_test_key_2")
    
    _, container, _ = test_engine_setup
    
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")
    # 清空可能由其他测试或真实.env文件加载的池
    key_manager._pools.clear() 
    # 使用模拟的 env var 重新注册提供商
    key_manager.register_provider("gemini", "GEMINI_API_KEYS")
    
    service: LLMServiceInterface = container.resolve("llm_service")
    
    return service, key_manager

# --- Fixture for E2E Tests ---

@pytest.fixture
def e2e_llm_service(test_engine_setup: Tuple[None, Container, None]) -> LLMServiceInterface:
    """
    【E2E测试专用 Fixture】
    提供一个配置了【真实】API密钥（从.env文件加载）的 LLMService。
    这个 fixture 不使用 monkeypatch，以确保环境的纯净。
    """
    _, container, _ = test_engine_setup
    
    # 应用启动时，test_engine_setup 已经隐式地加载了 .env 文件。
    # 为了确保隔离性，我们强制重新加载，以防被其他测试（理论上不应该）污染。
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")
    key_manager._pools.clear()
    # KeyPoolManager 会自动从 os.getenv('GEMINI_API_KEYS') 加载真实密钥
    key_manager.register_provider("gemini", "GEMINI_API_KEYS")
    
    service: LLMServiceInterface = container.resolve("llm_service")
    return service

# --- Test Suite for Real Providers (Unit/Integration) ---

class TestLLMServiceLogic:
    """
    测试 LLMService 与需要 API 密钥的真实提供商（以 Gemini 为例）的【内部逻辑】。
    这些测试使用【模拟密钥】，并对外部网络调用进行 mock。
    """

    async def test_request_success_on_first_try(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = success_response
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response.status == LLMResponseStatus.SUCCESS
            assert response.content == "Success!"
            mock_generate.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        retryable_exception = google_exceptions.ServiceUnavailable("503 Service Unavailable")
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")

        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = [retryable_exception, success_response]
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response.status == LLMResponseStatus.SUCCESS
            assert response.content == "Success after retry!"
            assert mock_generate.call_count == 2

    async def test_final_failure_after_all_retries(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        retryable_exception = google_exceptions.ServiceUnavailable("503 Service Unavailable")
        
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = retryable_exception
            
            with pytest.raises(LLMRequestFailedError) as exc_info:
                # 这里的重试是由内层的 _attempt_request_with_key 上的 tenacity 装饰器处理的
                # 外层的 request 方法会捕获最终的异常
                await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            # 确认 tenacity 确实重试了3次
            assert mock_generate.call_count == 3
            assert exc_info.value.last_error.error_type == LLMErrorType.PROVIDER_ERROR

    async def test_key_is_banned_on_authentication_error_and_switches(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, key_manager = unit_test_llm_service
        auth_exception = google_exceptions.PermissionDenied("401 Invalid API Key")
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success with second key")

        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = [auth_exception, success_response]
            
            # 第一次请求应该失败并禁用第一个密钥，第二次请求应该使用第二个密钥并成功
            # 整个过程由 request 方法的外层循环处理，对调用者透明
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Request that will switch keys")

            # 最终我们应该得到成功的响应
            assert response.status == LLMResponseStatus.SUCCESS
            assert response.content == "Success with second key"

            # 检查密钥池状态
            pool = key_manager.get_pool("gemini")
            assert pool.get_key_by_string("unit_test_key_1").status == KeyStatus.BANNED
            assert pool.get_key_by_string("unit_test_key_2").status == KeyStatus.AVAILABLE
            
            # 确认 generate 被调用了两次，分别使用了不同的密钥
            mock_generate.assert_has_calls([
                call(prompt="Request that will switch keys", model_name='gemini-1.5-pro', api_key='unit_test_key_1'),
                call(prompt="Request that will switch keys", model_name='gemini-1.5-pro', api_key='unit_test_key_2')
            ])

# --- Test Suite for Mock Provider ---
class TestLLMServiceWithMockProvider:

    async def test_mock_provider_request_succeeds(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, _ = unit_test_llm_service
        
        # 我们 patch MockProvider 的 generate 方法来隔离测试
        with patch.object(MockProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Verified Mock Call")
            
            response = await llm_service.request(model_name="mock/any-model", prompt="Test Prompt")
            
            assert response.status == LLMResponseStatus.SUCCESS
            assert response.content == "Verified Mock Call"
            mock_generate.assert_awaited_once()

    async def test_mock_provider_does_not_use_key_manager(self, unit_test_llm_service: Tuple[LLMServiceInterface, KeyPoolManager]):
        llm_service, key_manager = unit_test_llm_service
        
        # 我们监视 KeyPoolManager 的 acquire_key 方法
        with patch.object(key_manager, 'acquire_key', new_callable=AsyncMock) as mock_acquire_key:
            # 调用 mock provider
            await llm_service.request(model_name="mock/any-model", prompt="Test")
            
            # 断言 acquire_key 从未被调用
            mock_acquire_key.assert_not_called()

# --- Test Suite for E2E ---
class TestLLMEndToEnd:
    @pytest.mark.e2e
    async def test_real_gemini_api_request(self, e2e_llm_service: LLMServiceInterface):
        """
        【端到端测试】
        验证服务是否能成功调用真实的 Gemini API。
        这个测试需要有效的 GEMINI_API_KEYS 环境变量，并且会产生少量费用。
        使用 'pytest -m e2e' 命令来运行它。
        """
        llm_service = e2e_llm_service
        model_name = "gemini/gemini-1.5-flash" 
        prompt = "天空是什么颜色的？请用中文简短回答。"

        try:
            # 这个调用会使用.env中的真实密钥
            response = await llm_service.request(model_name=model_name, prompt=prompt)
        except LLMRequestFailedError as e:
            pytest.fail(f"Real API request failed unexpectedly: {e}")
        
        assert response is not None
        assert response.status == LLMResponseStatus.SUCCESS, f"API request failed: {response.error_details.message if response.error_details else 'No details'}"
        assert response.content is not None and len(response.content.strip()) > 0
        
        # 打印响应以供调试
        print(f"\nReal Gemini API Response: '{response.content.strip()}'")

        assert response.usage is not None
        assert response.usage["total_tokens"] > 0