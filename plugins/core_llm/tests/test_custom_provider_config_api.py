# plugins/core_llm/tests/test_custom_provider_config_api.py

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from plugins.core_llm.config_api import config_api_router, CustomProviderConfig
from plugins.core_llm.manager import KeyPoolManager
from backend.core.contracts import Container


@pytest.fixture
def test_app(mock_key_manager):
    """创建测试用的 FastAPI 应用，并注入模拟的依赖。"""
    app = FastAPI()
    
    # 创建一个模拟的容器
    mock_container = Mock(spec=Container)
    mock_container.resolve.return_value = mock_key_manager
    
    # 将容器附加到 app.state
    app.state.container = mock_container
    
    app.include_router(config_api_router)
    return app


@pytest.fixture
def mock_key_manager():
    """创建模拟的 KeyPoolManager。"""
    return Mock(spec=KeyPoolManager)


class TestCustomProviderConfigAPI:
    """测试自定义提供商配置 API。"""

    def test_get_custom_provider_configuration(self, test_app, mock_key_manager):
        """测试获取自定义提供商配置。"""
        # 设置模拟返回值
        mock_key_manager.get_custom_provider_config.return_value = {
            "base_url": "https://api.openai.com",
            "model_mapping": '{"proxy":"gemini/gemini-1.5-pro"}'
        }
        
        client = TestClient(test_app)
        response = client.get("/api/llm/config/custom_provider")
        
        assert response.status_code == 200
        data = response.json()
        assert data["base_url"] == "https://api.openai.com"
        assert data["model_mapping"] == '{"proxy":"gemini/gemini-1.5-pro"}'
        mock_key_manager.get_custom_provider_config.assert_called_once()

    def test_get_custom_provider_configuration_empty(self, test_app, mock_key_manager):
        """测试获取空的自定义提供商配置。"""
        # 设置模拟返回值为空配置
        mock_key_manager.get_custom_provider_config.return_value = {
            "base_url": None,
            "model_mapping": None
        }
        
        client = TestClient(test_app)
        response = client.get("/api/llm/config/custom_provider")
        
        assert response.status_code == 200
        data = response.json()
        assert data["base_url"] is None
        assert data["model_mapping"] is None

    def test_update_custom_provider_configuration_success(self, test_app, mock_key_manager):
        """测试成功更新自定义提供商配置。"""
        mock_key_manager.set_custom_provider_config.return_value = None
        
        client = TestClient(test_app)
        response = client.put(
            "/api/llm/config/custom_provider",
            json={
                "base_url": "https://api.groq.com/openai",
                "model_mapping": "llama3:gemini/gemini-1.5-pro"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Custom provider configuration updated" in data["message"]
        mock_key_manager.set_custom_provider_config.assert_called_once_with(
            "https://api.groq.com/openai",
            "llama3:gemini/gemini-1.5-pro"
        )

    def test_update_custom_provider_configuration_clear_config(self, test_app, mock_key_manager):
        """测试清除自定义提供商配置。"""
        mock_key_manager.set_custom_provider_config.return_value = None
        
        client = TestClient(test_app)
        response = client.put(
            "/api/llm/config/custom_provider",
            json={
                "base_url": None,
                "model_mapping": None
            }
        )
        
        assert response.status_code == 200
        mock_key_manager.set_custom_provider_config.assert_called_once_with(None, None)

    def test_update_custom_provider_configuration_error(self, test_app, mock_key_manager):
        """测试更新配置时发生错误。"""
        mock_key_manager.set_custom_provider_config.side_effect = Exception("Config update failed")
        
        client = TestClient(test_app)
        response = client.put(
            "/api/llm/config/custom_provider",
            json={
                "base_url": "https://api.openai.com",
                "model_mapping": "{}"
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Config update failed" in data["detail"]

    def test_custom_provider_config_model_validation(self):
        """测试 CustomProviderConfig 模型的验证。"""
        # 测试有效配置
        config = CustomProviderConfig(
            base_url="https://api.openai.com",
            model_mapping='{"test":"gemini/gemini-1.5-pro"}'
        )
        assert config.base_url == "https://api.openai.com"
        assert config.model_mapping == '{"test":"gemini/gemini-1.5-pro"}'
        
        # 测试空配置
        empty_config = CustomProviderConfig()
        assert empty_config.base_url is None
        assert empty_config.model_mapping is None
        
        # 测试部分配置
        partial_config = CustomProviderConfig(base_url="https://api.groq.com")
        assert partial_config.base_url == "https://api.groq.com"
        assert partial_config.model_mapping is None
