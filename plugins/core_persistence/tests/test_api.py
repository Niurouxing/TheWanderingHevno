# plugins/core_persistence/tests/test_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_persistence_api_exists(async_client: AsyncClient):
    """
    测试场景：当只加载 `core_persistence` 插件时，它的 API 端点应该存在。
    """
    # 1. 使用 fixture 创建一个只包含 `core_persistence` 的应用客户端
    # `core-logging` 会被自动包含
    client = await async_client(["core-persistence"])
    
    # 2. 向插件的 API 端点发送请求
    response = await client.get("/api/persistence/assets")
    
    # 3. 断言结果
    assert response.status_code == 200
    assert response.json() == {"message": "Asset listing endpoint for core_persistence."}

@pytest.mark.asyncio
async def test_api_does_not_exist_without_plugin(async_client: AsyncClient):
    """
    测试场景：当不加载 `core_persistence` 插件时，它的 API 端点不应该存在。
    """
    # 1. 创建一个只包含 `core-logging` 的应用 (或者一个不存在的虚拟插件)
    client = await async_client(["core-logging"]) 
    
    # 2. 向本应不存在的端点发送请求
    response = await client.get("/api/persistence/assets")
    
    # 3. 断言它返回 404 Not Found
    assert response.status_code == 404