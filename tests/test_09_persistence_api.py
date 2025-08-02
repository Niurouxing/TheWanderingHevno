# tests/test_09_persistence_api.py

import pytest
import io
import json
import zipfile
from uuid import UUID

from fastapi.testclient import TestClient
from backend.models import GraphCollection
from backend.core.state import Sandbox, SnapshotStore

# pytest 会自动发现并使用 conftest.py 中的 fixtures，无需显式导入

class TestPersistenceAPI:
    """
    测试与持久化相关的 API 端点 (/api/sandboxes/import, /api/sandboxes/{id}/export)
    """

    def test_sandbox_export_import_roundtrip(
        self,
        test_client: TestClient,
        linear_collection: GraphCollection,
    ):
        """
        测试一个完整的导出和导入流程（往返测试）。
        1. 创建一个沙盒并执行一步以生成历史记录。
        2. 导出该沙盒为一个 .hevno.zip 文件。
        3. 验证导出的文件结构和内容。
        4. 清理状态，模拟一个新环境。
        5. 导入之前导出的文件。
        6. 验证沙盒和其历史记录是否被成功恢复。
        """
        # --- 步骤 1 & 2: 创建沙盒，执行一步，然后导出 ---
        create_response = test_client.post(
            "/api/sandboxes",
            json={
                "name": "Export-Test-Sandbox",
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {"counter": 0}
            }
        )
        assert create_response.status_code == 200
        sandbox_data = create_response.json()
        sandbox_id = sandbox_data["id"]

        # 执行一步以产生更多历史快照
        step_response = test_client.post(
            f"/api/sandboxes/{sandbox_id}/step",
            json={"user_message": "test input"}
        )
        assert step_response.status_code == 200
        
        # 导出沙盒
        export_response = test_client.get(f"/api/sandboxes/{sandbox_id}/export")
        assert export_response.status_code == 200
        
        # --- 步骤 3: 验证导出的 ZIP 文件 ---
        assert export_response.headers["content-type"] == "application/zip"
        assert "attachment" in export_response.headers["content-disposition"]
        assert export_response.headers["content-disposition"].endswith(".hevno.zip")

        zip_bytes = export_response.content
        zip_buffer = io.BytesIO(zip_bytes)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            filenames = zf.namelist()
            # 应该包含 manifest, sandbox.json, 和 2 个快照 (genesis + 1 step)
            assert "manifest.json" in filenames
            assert "data/sandbox.json" in filenames
            snapshot_files = [f for f in filenames if f.startswith("data/snapshots/")]
            assert len(snapshot_files) == 2

            # 验证 manifest 内容
            manifest_content = zf.read("manifest.json").decode('utf-8')
            manifest = json.loads(manifest_content)
            assert manifest["package_type"] == "sandbox_archive"
            assert manifest["entry_point"] == "sandbox.json"

        # --- 步骤 4: 清理状态，模拟新环境 ---
        # 注意：test_client fixture 会在测试结束后清理，但我们需要在测试中途清理
        sandbox_store: dict = test_client.app.state.sandbox_store
        snapshot_store: SnapshotStore = test_client.app.state.snapshot_store
        sandbox_store.clear()
        snapshot_store.clear()

        # --- 步骤 5: 导入 ZIP 文件 ---
        import_response = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("imported_sandbox.hevno.zip", zip_bytes, "application/zip")}
        )
        
        assert import_response.status_code == 200
        imported_sandbox_data = import_response.json()
        
        # --- 步骤 6: 验证恢复的状态 ---
        assert imported_sandbox_data["id"] == sandbox_id
        assert imported_sandbox_data["name"] == "Export-Test-Sandbox"
        
        # 检查新环境中的 sandbox store
        assert len(sandbox_store) == 1
        assert UUID(sandbox_id) in sandbox_store
        
        # 调用 history 端点来验证快照是否已全部恢复
        history_response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert len(history_data) == 2 # 确认两个快照都被恢复

    def test_import_invalid_file_type(self, test_client: TestClient):
        """测试上传非 .hevno.zip 文件时应被拒绝。"""
        response = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("test.txt", b"this is not a zip", "text/plain")}
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_import_zip_missing_manifest(self, test_client: TestClient):
        """测试导入缺少 manifest.json 的 zip 文件。"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("data/somefile.txt", "hello")
        
        zip_bytes = zip_buffer.getvalue()

        response = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("no_manifest.hevno.zip", zip_bytes, "application/zip")}
        )
        assert response.status_code == 400
        assert "missing 'manifest.json'" in response.json()["detail"]

    def test_import_conflicting_sandbox_id(self, test_client: TestClient, linear_collection: GraphCollection):
        """测试当导入的沙盒 ID 已存在时，应返回 409 Conflict。"""
        # 1. 先创建一个沙盒并导出，得到一个合法的 zip 文件
        create_response = test_client.post(
            "/api/sandboxes",
            json={"name": "Existing Sandbox", "graph_collection": linear_collection.model_dump()}
        )
        assert create_response.status_code == 200
        sandbox_id = create_response.json()["id"]

        export_response = test_client.get(f"/api/sandboxes/{sandbox_id}/export")
        assert export_response.status_code == 200
        zip_bytes = export_response.content

        # 2. 此时沙盒已存在，再次尝试导入同一个 zip 文件
        import_response = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("conflict.hevno.zip", zip_bytes, "application/zip")}
        )
        
        # 3. 验证是否返回冲突错误
        assert import_response.status_code == 409
        assert "already exists" in import_response.json()["detail"]