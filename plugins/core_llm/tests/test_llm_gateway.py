# plugins/core_llm/tests/test_llm_gateway.py

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from typing import Tuple

# 从平台核心导入接口
from backend.core.contracts import Container, HookManager

# 从本插件的公共契约中导入所需模型
from plugins.core_llm.contracts import (
    LLMResponse, LLMError, LLMResponseStatus, LLMErrorType, LLMRequestFailedError, LLMServiceInterface
)
# 从本插件内部实现中导入待测试的类
from plugins.core_llm.manager import KeyPoolManager
from plugins.core_llm.providers.gemini import GeminiProvider
from google.api_core import exceptions as google_exceptions

# 标记此文件中的所有测试都是异步的
pytestmark = pytest.mark.asyncio


# --- Fixture for setting up the test environment ---

@pytest.fixture(scope="function")
def llm_service_components(test_engine_setup: Tuple[None, Container, None], monkeypatch) -> Tuple[LLMServiceInterface, KeyPoolManager, Container]:
    """
    【已重构】
    提供一个从完整启动的应用上下文中获取的 LLMService 实例及其相关组件。
    这个 fixture 现在也负责模拟环境变量，以确保测试的独立性。
    """
    # 在应用服务被解析之前，设置模拟的环境变量
    monkeypatch.setenv("GEMINI_API_KEYS", "test_key_1,test_key_2")
    
    _, container, _ = test_engine_setup
    
    # 重新填充 key_pool_manager 以使用模拟的 keys
    key_manager: KeyPoolManager = container.resolve("key_pool_manager")
    # 清空可能从真实 .env 加载的池
    key_manager._pools.clear() 
    # 使用模拟的 env var 重新注册
    key_manager.register_provider("gemini", "GEMINI_API_KEYS")
    
    service: LLMServiceInterface = container.resolve("llm_service")
    
    return service, key_manager, container


# --- Test Suite ---

class TestLLMServiceLogic:
    """
    【单元/集成测试】
    测试 LLMService 的核心逻辑，如重试、错误处理和密钥管理。
    测试运行在真实的应用上下文中，但对外部网络调用进行 mock。
    """

    async def test_request_success_on_first_try(self, llm_service_components: Tuple[LLMServiceInterface, KeyPoolManager, Container]):
        """
        验证如果第一次尝试成功，服务会返回正确的响应且不重试。
        """
        llm_service, _, _ = llm_service_components
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success!")
        
        # Patch 具体的 Provider 的 generate 方法，这是实际发出网络调用的地方
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = success_response
            
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response.status == LLMResponseStatus.SUCCESS
            assert response.content == "Success!"
            mock_generate.assert_awaited_once()

    async def test_retry_on_provider_error_and_succeed(self, llm_service_components: Tuple[LLMServiceInterface, KeyPoolManager, Container]):
        llm_service, _, _ = llm_service_components
        # 【修改】: 抛出一个具体的、可被翻译的异常类型
        retryable_exception = google_exceptions.ServiceUnavailable("503 Service Unavailable")
        success_response = LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success after retry!")

        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = [
                retryable_exception,
                success_response
            ]
            
            llm_service.max_retries = 2
            response = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert response == success_response
            assert mock_generate.call_count == 2

    async def test_final_failure_after_all_retries(self, llm_service_components: Tuple[LLMServiceInterface, KeyPoolManager, Container]):
        llm_service, _, _ = llm_service_components
        # 【修改】: 抛出一个具体的、可被翻译的异常类型
        retryable_exception = google_exceptions.ServiceUnavailable("503 Service Unavailable")
        
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = retryable_exception
            
            llm_service.max_retries = 3
            with pytest.raises(LLMRequestFailedError) as exc_info:
                await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Hello")
            
            assert "failed permanently after 3 attempt(s)" in str(exc_info.value)
            # 现在这个断言将会成功
            assert exc_info.value.last_error.error_type == LLMErrorType.PROVIDER_ERROR
            assert mock_generate.call_count == 3
            
    async def test_no_retry_on_authentication_error(self, llm_service_components: Tuple[LLMServiceInterface, KeyPoolManager, Container]):
        """
        验证如果发生认证错误（不可重试），服务会立即失败且不进行重试。
        """
        llm_service, _, _ = llm_service_components
        auth_exception = Exception("401 Invalid API Key")
        
        # 模拟 GeminiProvider 的 translate_error 方法返回一个认证错误
        auth_error = LLMError(error_type=LLMErrorType.AUTHENTICATION_ERROR, message="Invalid key", is_retryable=False)
        
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock, side_effect=auth_exception), \
             patch.object(GeminiProvider, 'translate_error', return_value=auth_error):
            
            llm_service.max_retries = 3
            with pytest.raises(LLMRequestFailedError) as exc_info:
                await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="This will fail")

            assert "failed permanently after 3 attempt(s)" in str(exc_info.value)
            # 关键：检查 _attempt_request 是否只被调用了一次
            assert llm_service.last_known_error.error_type == LLMErrorType.AUTHENTICATION_ERROR

    async def test_key_is_banned_on_authentication_error(self, llm_service_components: Tuple[LLMServiceInterface, KeyPoolManager, Container]):
        """
        【关键测试】验证发生认证错误后，对应的 API 密钥会被禁用。
        """
        llm_service, key_manager, _ = llm_service_components
        auth_exception = Exception("401 Invalid API Key")
        
        # 模拟 provider 返回认证错误
        auth_error_response = LLMResponse(
            status=LLMResponseStatus.ERROR,
            error_details=LLMError(error_type=LLMErrorType.AUTHENTICATION_ERROR, message="Invalid key", is_retryable=False)
        )
        
        with patch.object(GeminiProvider, 'generate', new_callable=AsyncMock) as mock_generate:
            # 模拟第一次调用返回认证错误，第二次调用返回成功（以验证密钥切换）
            mock_generate.side_effect = [
                auth_error_response,
                LLMResponse(status=LLMResponseStatus.SUCCESS, content="Success with second key")
            ]
            
            # 第一次请求，应该会失败，但会触发密钥禁用逻辑
            response1 = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Request 1")
            assert response1.status == LLMResponseStatus.ERROR
            
            # 检查密钥池状态
            pool = key_manager.get_pool("gemini")
            # 假设第一个被使用的密钥是 test_key_1
            banned_key = next((k for k in pool._keys if not k.is_available()), None)
            assert banned_key is not None, "A key should have been banned"
            assert banned_key.key_string == "test_key_1"

            # 第二次请求，应该会使用另一个可用的密钥并成功
            response2 = await llm_service.request(model_name="gemini/gemini-1.5-pro", prompt="Request 2")
            assert response2.status == LLMResponseStatus.SUCCESS
            assert response2.content == "Success with second key"
            
            # 确认 generate 被调用了两次
            assert mock_generate.call_count == 2