# plugins/core_llm/tests/test_openai_compatible_provider.py

import pytest
import httpx
import os
import dotenv
from unittest.mock import AsyncMock, patch, Mock
from typing import Tuple, AsyncGenerator

# --- 核心 & 平台导入 ---
from backend.core.contracts import Container
from backend.app import create_app
from fastapi import FastAPI
from httpx import AsyncClient

# --- 插件导入 ---
from plugins.core_llm.__init__ import populate_llm_services
from plugins.core_llm.registry import ProviderRegistry
from plugins.core_llm.manager import KeyPoolManager
from plugins.core_llm.factory import ProviderFactory
from plugins.core_llm.providers.openai_compatible import OpenAICompatibleProvider
from plugins.core_llm.contracts import LLMResponseStatus, LLMErrorType


class TestOpenAICompatibleProviderUnit:
    """
    【单元测试】
    隔离测试 OpenAICompatibleProvider 类本身的行为。
    """

    def test_init_with_valid_url(self):
        provider = OpenAICompatibleProvider("https://api.openai.com")
        assert provider.base_url == "https://api.openai.com/v1"

    def test_init_adds_v1_to_url(self):
        provider = OpenAICompatibleProvider("https://api.groq.com/openai")
        assert provider.base_url == "https://api.groq.com/openai/v1"

    def test_init_with_model_mapping(self):
        mapping = {"proxy-model": "real-model-name"}
        provider = OpenAICompatibleProvider("https://api.example.com", mapping)
        assert provider.model_mapping == mapping
        assert provider.get_underlying_model("proxy-model") == "real-model-name"

    def test_init_without_base_url_raises_error(self):
        with pytest.raises(ValueError, match="requires a 'base_url'"):
            OpenAICompatibleProvider("")

    @pytest.mark.asyncio
    async def test_generate_success(self):
        provider = OpenAICompatibleProvider("https://api.example.com")
        mock_response_data = {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "model": "gpt-4o", "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        
        with patch.object(provider.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_http_response = AsyncMock()
            mock_http_response.json = AsyncMock(return_value=mock_response_data)
            mock_http_response.raise_for_status = Mock(return_value=None)
            mock_post.return_value = mock_http_response
            
            result = await provider.generate(
                messages=[{"role": "user", "content": "Hello"}],
                model_name="gpt-4o", api_key="test-key", temperature=0.5
            )
            
            assert result.status == LLMResponseStatus.SUCCESS
            assert result.content == "Hello, world!"
            assert result.final_request_payload is not None
            assert result.final_request_payload["payload"]["temperature"] == 0.5

    def test_translate_error_network_error(self):
        provider = OpenAICompatibleProvider("https://api.example.com")
        network_error = httpx.RequestError("Connection failed", request=AsyncMock())
        translated = provider.translate_error(network_error)
        assert translated.error_type == LLMErrorType.NETWORK_ERROR
        assert translated.is_retryable is True


@pytest.mark.asyncio
class TestDynamicProviderIntegration:
    """
    【集成测试】
    测试基于环境变量的动态提供商加载和注册机制。
    """
    async def test_populate_services_with_custom_provider(
        self, test_engine_setup: Tuple[None, Container, None], monkeypatch
    ):
        monkeypatch.setenv("HEVNO_LLM_PROVIDERS", "my_groq")
        monkeypatch.setenv("PROVIDER_MY_GROQ_TYPE", "openai_compatible")
        monkeypatch.setenv("PROVIDER_MY_GROQ_BASE_URL", "https://api.groq.com/openai")
        monkeypatch.setenv("PROVIDER_MY_GROQ_KEYS_ENV", "GROQ_API_KEYS")
        monkeypatch.setenv("PROVIDER_MY_GROQ_MODEL_MAPPING", "llama3:real-llama-model")
        monkeypatch.setenv("GROQ_API_KEYS", "gsk_1234")

        _, container, hook_manager = test_engine_setup
        await populate_llm_services(container, hook_manager)

        provider_registry: ProviderRegistry = container.resolve("provider_registry")
        provider_instance = provider_registry.get("my_groq")
        assert provider_instance is not None
        assert isinstance(provider_instance, OpenAICompatibleProvider)
        assert provider_instance.base_url == "https://api.groq.com/openai/v1"
        assert provider_instance.model_mapping == {"llama3": "real-llama-model"}
        
        key_manager: KeyPoolManager = container.resolve("key_pool_manager")
        key_pool = key_manager.get_pool("my_groq")
        assert key_pool is not None
        assert key_pool.get_key_count() == 1


# --- E2E 测试的 Fixture 定义 ---

@pytest.fixture(scope="function")
def temp_env_file(tmp_path, monkeypatch):
    """
    【已修正】
    这个 fixture 现在负责在 app 启动前，准备好一个包含初始配置的 .env 文件，
    并确保 dotenv 会加载它。
    """
    env_path = tmp_path / ".env"
    initial_content = (
        'HEVNO_LLM_PROVIDERS="reload_test"\n'
        'PROVIDER_RELOAD_TEST_TYPE="openai_compatible"\n'
        'PROVIDER_RELOAD_TEST_BASE_URL="https://initial.api.com"\n'
        'PROVIDER_RELOAD_TEST_KEYS_ENV="RELOAD_KEYS"\n'
    )
    env_path.write_text(initial_content)
    
    # 指向我们的临时文件
    monkeypatch.setattr(dotenv, 'find_dotenv', lambda: str(env_path))
    
    # 强制从该文件加载环境变量，覆盖所有现有变量
    dotenv.load_dotenv(dotenv_path=env_path, override=True)
    
    yield env_path


@pytest.fixture(scope="function")
def app(temp_env_file) -> FastAPI:
    """
    【已修正】
    这个 fixture 现在依赖于 `temp_env_file`。
    这强制 pytest 先运行环境设置，然后再创建应用实例。
    """
    return create_app()


@pytest.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    【已修正】
    这个 fixture 显式地管理应用的生命周期，确保启动逻辑完全执行。
    """
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client_instance:
            yield client_instance


@pytest.mark.e2e
@pytest.mark.asyncio
class TestLLMConfigAPI_E2E:
    """
    【端到端 E2E 测试】
    测试 /api/llm/config/ 下的 API 端点，特别是热重载功能。
    """
    async def test_api_reload_updates_provider_factory(
        self, app: FastAPI, client: AsyncClient, temp_env_file
    ):
        """
        【已修正】
        测试 /reload API 能否在运行时读取更新后的环境变量，并热更新服务。
        """
        # 1. 获取容器。由于 fixture 依赖关系已修正，此时容器应该已正确初始化。
        try:
            container: Container = app.state.container
        except AttributeError:
            pytest.fail("app.state.container was not set. The application lifespan did not run correctly.")

        # 2. 验证初始状态
        #    应用的启动过程现在应该已经正确读取了 temp_env_file 的内容。
        initial_factory: ProviderFactory = container.resolve("provider_factory_reload_test")
        initial_provider: OpenAICompatibleProvider = initial_factory.get_provider()
        assert initial_provider.base_url == "https://initial.api.com/v1"

        # 3. 模拟外部变更：直接修改 .env 文件内容
        dotenv.set_key(str(temp_env_file), "PROVIDER_RELOAD_TEST_BASE_URL", "https://reloaded.api.com")

        # 4. 触发被测试的行为：调用 /reload API
        response = await client.post("/api/llm/config/reload")
        assert response.status_code == 200, response.text
        assert "reloaded successfully" in response.json()["message"]

        # 5. 验证最终状态
        reloaded_factory: ProviderFactory = container.resolve("provider_factory_reload_test")
        assert reloaded_factory is initial_factory, "The factory instance itself should not change."

        reloaded_provider: OpenAICompatibleProvider = reloaded_factory.get_provider()
        assert reloaded_provider is not initial_provider, "The provider instance should have been recreated."
        assert reloaded_provider.base_url == "https://reloaded.api.com/v1"