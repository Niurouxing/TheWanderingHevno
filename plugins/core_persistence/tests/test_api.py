# plugins/core_persistence/tests/test_api.py
import pytest
import io
import zipfile
from httpx import AsyncClient

# 保持你现有的测试
@pytest.mark.asyncio
async def test_persistence_api_exists(async_client):
    client = await async_client(["core-persistence"])
    response = await client.get("/api/persistence/assets")
    assert response.status_code == 200
    assert response.json() == {"message": "Asset listing endpoint for core_persistence."}

@pytest.mark.asyncio
async def test_api_does_not_exist_without_plugin(async_client):
    client = await async_client(["core-logging"]) 
    response = await client.get("/api/persistence/assets")
    assert response.status_code == 404

# --- 新增的 API 功能测试 ---

@pytest.mark.asyncio
async def test_import_package_api_success(async_client):
    """
    测试成功导入一个合法的 .hevno.zip 包。
    """
    # 1. 动态创建一个合法的 zip 包
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        manifest_content = """
        {
            "package_type": "graph_collection",
            "entry_point": "main.json",
            "metadata": {"author": "Test"}
        }
        """
        zf.writestr("manifest.json", manifest_content)
        zf.writestr("data/main.json", '{"name": "test_graph"}')

    zip_bytes = zip_buffer.getvalue()

    # 2. 创建一个只包含 core-persistence 的客户端
    client = await async_client(["core-persistence"])

    # 3. 发送 POST 请求
    files = {'file': ('test.hevno.zip', zip_bytes, 'application/zip')}
    response = await client.post("/api/persistence/package/import", files=files)

    # 4. 断言结果
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['package_type'] == 'graph_collection'
    assert response_data['metadata']['author'] == 'Test'


@pytest.mark.asyncio
async def test_import_package_api_invalid_file(async_client):
    """
    测试上传非 zip 文件或无效 zip 时的错误处理。
    """
    client = await async_client(["core-persistence"])

    # 场景1：非 .hevno.zip 文件名
    files = {'file': ('test.txt', b'hello', 'text/plain')}
    response = await client.post("/api/persistence/package/import", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()['detail']

    # 场景2：缺少 manifest 的 zip 文件
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("data/main.json", '{"name": "test_graph"}')
    zip_bytes = zip_buffer.getvalue()
    
    files = {'file': ('bad.hevno.zip', zip_bytes, 'application/zip')}
    response = await client.post("/api/persistence/package/import", files=files)
    assert response.status_code == 400
    assert "missing 'manifest.json'" in response.json()['detail']