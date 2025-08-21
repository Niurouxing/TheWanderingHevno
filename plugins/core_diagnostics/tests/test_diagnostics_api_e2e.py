# plugins/core_diagnostics/tests/test_diagnostics_api_e2e.py

import pytest
from httpx import AsyncClient

# 标记此文件中所有测试均为端到端(e2e)测试
pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]


class TestDiagnosticsAPI:
    """
    【E2E测试】
    测试由 `core_diagnostics` 插件提供的诊断相关API端点。
    """

    async def test_get_system_report(self, client: AsyncClient):
        """
        验证 `/api/system/report` 端点能成功返回一个结构正确的报告。
        这个API现在由 core_diagnostics 插件提供。
        """
        response = await client.get("/api/system/report")
        
        assert response.status_code == 200, f"获取系统报告失败: {response.text}"
        report = response.json()
        
        # 验证报告中包含关键的顶层键，这些键由不同的报告器提供
        assert "plugins" in report, "报告中应包含 'plugins' 键"
        assert "llm_providers" in report, "报告中应包含 'llm_providers' 键"
        
        # 验证 'plugins' 报告器（由 core_diagnostics 自己提供）工作正常
        assert "backend" in report["plugins"]
        
        # 验证报告中能找到核心插件的信息
        # 注意：现在 core_api 的 manifest 应该被找到了
        core_api_plugin = next((p for p in report["plugins"]["backend"] if p.get("id") == "core_api"), None)
        assert core_api_plugin is not None
        assert core_api_plugin["version"] == "1.0.0"

        # 验证 'llm_providers' 报告器（由 core_llm 提供）工作正常
        assert "gemini" in report["llm_providers"]
        assert "mock" in report["llm_providers"]