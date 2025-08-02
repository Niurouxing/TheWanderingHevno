# plugins/core_persistence/tests/test_persistence_api.py

import pytest
import io
import json
import zipfile
from uuid import UUID

from fastapi.testclient import TestClient
from backend.core.contracts import GraphCollection, Container, SnapshotStoreInterface

@pytest.mark.e2e
class TestPersistenceAPI:
    """测试与持久化相关的 API 端点。"""


    def test_list_assets_is_empty(self, test_client: TestClient):
        # 这是一个新的、针对 persistence 插件 API 的简单测试
        response = test_client.get("/api/persistence/assets/graph")
        assert response.status_code == 200
        assert response.json() == []

    def test_import_invalid_package(self, test_client: TestClient):
        # 测试通用的包导入端点
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("somefile.txt", "hello") # 缺少 manifest.json
        
        zip_bytes = zip_buffer.getvalue()

        response = test_client.post(
            "/api/persistence/package/import",
            files={"file": ("bad_package.hevno.zip", zip_bytes, "application/zip")}
        )
        assert response.status_code == 400
        assert "missing 'manifest.json'" in response.json()["detail"]