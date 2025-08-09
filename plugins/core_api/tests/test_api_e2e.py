# plugins/core_api/tests/test_api_e2e.py 

import pytest
import json
from httpx import AsyncClient
from pathlib import Path

# 标记此文件中所有测试均为端到端(e2e)测试
pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


class TestBaseRouterAPI:
    """
    【E2E测试】
    测试由 `base_router.py` 提供的系统级API端点。
    """

    async def test_get_system_report(self, client: AsyncClient):
        """
        验证 `/api/system/report` 端点能成功返回一个结构正确的报告。
        """
        response = await client.get("/api/system/report")
        
        assert response.status_code == 200, f"获取系统报告失败: {response.text}"
        report = response.json()
        
        # 验证报告中包含关键的顶层键
        assert "plugins" in report
        assert "backend" in report["plugins"]
        assert "llm_providers" in report
        
        # 验证报告中能找到核心插件的信息
        core_api_plugin = next((p for p in report["plugins"]["backend"] if p.get("id") == "core_api"), None)
        assert core_api_plugin is not None
        assert core_api_plugin["version"] == "1.0.0"

        # 验证报告中能找到LLM提供商的信息
        gemini_provider = next((p for p in report["llm_providers"] if p.get("name") == "gemini"), None)
        assert gemini_provider is not None

    async def test_get_backend_hooks_manifest(self, client: AsyncClient):
        """
        验证 `/api/system/hooks/manifest` 端点能返回一个后端已注册钩子的列表。
        """
        response = await client.get("/api/system/hooks/manifest")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hooks" in data
        assert isinstance(data["hooks"], list)
        
        # 验证一些关键的核心钩子确实存在于清单中
        assert "collect_api_routers" in data["hooks"]
        assert "services_post_register" in data["hooks"]



class TestSystemRouterAPI:
    """
    【E2E测试】
    测试由 `system_router.py` 提供的插件清单和静态资源服务API。
    """

    async def test_get_all_plugins_manifest(self, client: AsyncClient):
        """
        验证 `/api/plugins/manifest` 端点能返回所有已安装插件的 manifest.json 内容。
        """
        response = await client.get("/api/plugins/manifest")
        
        assert response.status_code == 200
        manifests = response.json()
        
        assert isinstance(manifests, list)
        # 检查是否至少有几个核心插件被加载
        assert len(manifests) > 3 
        
        manifest_ids = {m.get("id") for m in manifests}
        assert "core_api" in manifest_ids
        assert "core_engine" in manifest_ids
        assert "core_llm" in manifest_ids
        
    async def test_serve_plugin_resource_success(self, client: AsyncClient):
        """
        验证静态资源服务能成功返回一个插件内的文件。
        """
        # 我们请求 core_api 插件自己的 manifest.json 文件作为一个测试用例
        response = await client.get("/plugins/core_api/manifest.json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        # 将返回内容与实际文件内容进行比较
        file_path = Path(__file__).parent.parent / "manifest.json"
        with open(file_path, "r") as f:
            expected_content = json.load(f)
        
        assert response.json() == expected_content

    async def test_serve_plugin_resource_not_found(self, client: AsyncClient):
        """
        验证请求一个不存在的插件资源会返回 404 Not Found。
        """
        response = await client.get("/plugins/core_api/this_file_does_not_exist.js")
        assert response.status_code == 404

    @pytest.mark.skip(reason="Directory traversal test is invalid due to client-side and framework URL normalization.")
    async def test_serve_plugin_resource_directory_traversal_is_blocked(self, client: AsyncClient):
        """
        验证目录遍历攻击（使用 '..'）会被阻止并返回 403 Forbidden。
        """
        # 尝试从 core_api 插件目录向上遍历到 core_engine 插件目录
        response = await client.get("/plugins/core_api/../core_engine/manifest.json")
        
        # system_router.py 中的安全检查应该捕获这个并返回 403
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]