# plugins/core_llm/tests/test_openai_compatible_provider.py

import pytest
import httpx
from unittest.mock import AsyncMock, patch
from plugins.core_llm.providers.openai_compatible import OpenAICompatibleProvider
from plugins.core_llm.contracts import LLMResponseStatus, LLMErrorType


class TestOpenAICompatibleProvider:
    """测试 OpenAI 兼容提供商的基本功能。"""

    def test_init_with_valid_url(self):
        """测试使用有效 URL 初始化提供商。"""
        provider = OpenAICompatibleProvider("https://api.openai.com")
        assert provider.base_url == "https://api.openai.com/v1"

    def test_init_adds_v1_to_url(self):
        """测试初始化时自动添加 /v1 到 URL。"""
        provider = OpenAICompatibleProvider("https://api.groq.com/openai")
        assert provider.base_url == "https://api.groq.com/openai/v1"

    def test_init_preserves_v1_in_url(self):
        """测试如果 URL 已包含 /v1，则不重复添加。"""
        provider = OpenAICompatibleProvider("https://api.openai.com/v1")
        assert provider.base_url == "https://api.openai.com/v1"

    def test_init_with_model_mapping(self):
        """测试使用模型映射初始化提供商。"""
        mapping = {"proxy-model": "gemini/gemini-1.5-pro"}
        provider = OpenAICompatibleProvider("https://api.openai.com", mapping)
        assert provider.get_underlying_model("proxy-model") == "gemini/gemini-1.5-pro"
        assert provider.get_underlying_model("unknown-model") is None

    def test_init_without_base_url_raises_error(self):
        """测试不提供 base_url 会抛出错误。"""
        with pytest.raises(ValueError, match="requires a 'base_url'"):
            OpenAICompatibleProvider("")

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """测试成功的生成响应。"""
        provider = OpenAICompatibleProvider("https://api.openai.com")
        
        # 模拟成功的 HTTP 响应
        mock_response_data = {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "model": "gpt-4o",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        
        with patch.object(provider.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            result = await provider.generate(
                messages=[{"role": "user", "content": "Hello"}],
                model_name="gpt-4o",
                api_key="test-key"
            )
            
            assert result.status == LLMResponseStatus.SUCCESS
            assert result.content == "Hello, world!"
            assert result.model_name == "gpt-4o"
            assert result.usage is not None
            assert result.usage["prompt_tokens"] == 10

    @pytest.mark.asyncio
    async def test_generate_http_error_401(self):
        """测试 401 认证错误的处理。"""
        provider = OpenAICompatibleProvider("https://api.openai.com")
        
        with patch.object(provider.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=AsyncMock(), response=mock_response
            )
            
            result = await provider.generate(
                messages=[{"role": "user", "content": "Hello"}],
                model_name="gpt-4o",
                api_key="invalid-key"
            )
            
            assert result.status == LLMResponseStatus.ERROR
            assert result.error_details.error_type == LLMErrorType.AUTHENTICATION_ERROR
            assert "Invalid API key" in result.error_details.message

    @pytest.mark.asyncio
    async def test_generate_http_error_429(self):
        """测试 429 速率限制错误的处理。"""
        provider = OpenAICompatibleProvider("https://api.openai.com")
        
        with patch.object(provider.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_post.side_effect = httpx.HTTPStatusError(
                "Rate limit exceeded", request=AsyncMock(), response=mock_response
            )
            
            result = await provider.generate(
                messages=[{"role": "user", "content": "Hello"}],
                model_name="gpt-4o",
                api_key="test-key"
            )
            
            assert result.status == LLMResponseStatus.ERROR
            assert result.error_details.error_type == LLMErrorType.RATE_LIMIT_ERROR
            assert "Rate limit exceeded" in result.error_details.message

    def test_translate_error_network_error(self):
        """测试网络错误的翻译。"""
        provider = OpenAICompatibleProvider("https://api.openai.com")
        
        network_error = httpx.RequestError("Connection failed")
        translated = provider.translate_error(network_error)
        
        assert translated.error_type == LLMErrorType.NETWORK_ERROR
        assert "Network error" in translated.message
        assert translated.is_retryable is True

    def test_translate_error_unknown_error(self):
        """测试未知错误的翻译。"""
        provider = OpenAICompatibleProvider("https://api.openai.com")
        
        unknown_error = RuntimeError("Something went wrong")
        translated = provider.translate_error(unknown_error)
        
        assert translated.error_type == LLMErrorType.UNKNOWN_ERROR
        assert "An unknown error occurred" in translated.message
        assert translated.is_retryable is False
