# tests/conftest.py (或 plugins/core_codex/tests/conftest.py)

import pytest
import pytest_asyncio
# --- 【修改】从 httpx 额外导入 ASGITransport ---
from httpx import AsyncClient, ASGITransport 
from asgi_lifespan import LifespanManager
from uuid import UUID

from backend.main import app # 导入你的 FastAPI 应用实例
from plugins.core_engine.contracts import Sandbox

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="session")
async def client():
    """
    一个能在应用生命周期内与测试 FastAPI 应用交互的 AsyncClient。
    """
    async with LifespanManager(app):
        # --- 将 app 对象包装在 ASGITransport 中，并作为 transport 参数传递 ---
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

@pytest_asyncio.fixture
async def sandbox_in_db(client: AsyncClient) -> Sandbox:
    """
    一个 fixture，确保每个测试函数开始时都有一个干净的沙盒存在。
    """
    request_body = {
        "name": "Test Sandbox for API",
        "definition": {
            "initial_lore": {},
            "initial_moment": {}
        }
    }
    # 使用现有的 API 创建沙盒
    response = await client.post("/api/sandboxes", json=request_body)
    response.raise_for_status()
    sandbox_data = response.json()
    
    yield Sandbox.model_validate(sandbox_data)
    
    # 测试结束后通过 API 清理沙盒
    sandbox_id = sandbox_data["id"]
    await client.delete(f"/api/sandboxes/{sandbox_id}")