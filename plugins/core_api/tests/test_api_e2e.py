# plugins/core_api/tests/test_api_e2e.py

import pytest
import zipfile
import io
import json
from fastapi.testclient import TestClient
from uuid import uuid4, UUID

# 从平台核心契约导入
from backend.core.contracts import Container

# 从依赖插件的契约导入数据模型和接口
from plugins.core_engine.contracts import GraphCollection, SnapshotStoreInterface

# 注意：这个文件现在只依赖 test_client 和 conftest_data.py 中定义的 fixture
# 它与 test_engine fixture 完全解耦

@pytest.mark.e2e
class TestApiSandboxLifecycle:
    """测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        # 1. 创建沙盒
        response = test_client.post(
            "/api/sandboxes",
            json={
                "name": "E2E Test",
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {} 
            }
        )
        assert response.status_code == 201, response.text
        sandbox_data = response.json()
        sandbox_id = sandbox_data["id"]
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        # 2. 执行一步
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "test"})
        assert response.status_code == 200, response.text
        step1_snapshot_data = response.json()
        run_output = step1_snapshot_data.get("run_output", {})
        assert "C" in run_output
        assert run_output["C"]["llm_output"].startswith("[MOCK RESPONSE for mock/model]")

        # 3. 获取历史记录
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200, response.text
        history = response.json()
        assert len(history) == 2

        # 4. 回滚到创世快照
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200, response.text

@pytest.mark.e2e
class TestSystemReportAPI:
    """测试 /api/system/report 端点"""

    def test_get_system_report(self, test_client: TestClient):
        response = test_client.get("/api/system/report")
        assert response.status_code == 200, response.text
        report = response.json()

        # 验证报告中包含了由各插件提供的 key
        assert "llm_providers" in report
        
        # 验证 llm_providers 的内容
        assert isinstance(report["llm_providers"], list)
        gemini_provider_report = next((p for p in report["llm_providers"] if p["name"] == "gemini"), None)
        assert gemini_provider_report is not None

@pytest.mark.e2e
class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            json={"name": "Invalid Graph", "graph_collection": invalid_graph_no_main}
        )
        assert response.status_code == 422, response.text
        error_detail = response.json()["detail"][0]
        assert "A 'main' graph must be defined" in error_detail["msg"]

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = uuid4()
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404, response.text
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 404, response.text


@pytest.mark.e2e
class TestSandboxImportExport:
    """专门测试沙盒导入/导出 API 的类。"""

    def test_sandbox_export_import_roundtrip(
        self, test_client: TestClient, linear_collection: GraphCollection
    ):
        # --- 步骤 1 & 2: 创建沙盒，执行一步，然后导出 ---
        create_resp = test_client.post(
            "/api/sandboxes",
            json={"name": "Export-Test-Sandbox", "graph_collection": linear_collection.model_dump()}
        )
        assert create_resp.status_code == 201, create_resp.text
        sandbox_id = create_resp.json()["id"]

        step_resp = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert step_resp.status_code == 200, step_resp.text
        
        export_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/export")
        assert export_resp.status_code == 200, export_resp.text
        
        # --- 步骤 3: 验证导出的 ZIP 文件 ---
        zip_bytes = export_resp.content
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            filenames = zf.namelist()
            assert "manifest.json" in filenames
            assert "data/sandbox.json" in filenames
            assert len([f for f in filenames if f.startswith("data/snapshots/")]) == 2
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["package_type"] == "sandbox_archive"

        # --- 步骤 4: 清理状态，模拟新环境 ---
        container: Container = test_client.app.state.container
        sandbox_store: dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        sandbox_store.clear()
        snapshot_store.clear()

        # --- 步骤 5: 导入 ZIP 文件 ---
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("imported.hevno.zip", zip_bytes, "application/zip")}
        )
        assert import_resp.status_code == 200, import_resp.text
        imported_sandbox = import_resp.json()
        
        # --- 步骤 6: 验证恢复的状态 ---
        assert imported_sandbox["id"] == sandbox_id
        assert imported_sandbox["name"] == "Export-Test-Sandbox"
        assert len(sandbox_store) == 1
        
        history_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert history_resp.status_code == 200, history_resp.text
        assert len(history_resp.json()) == 2

    def test_import_invalid_package_type(self, test_client: TestClient):
        """测试导入一个非沙盒类型的包应被拒绝。"""
        manifest = {
            "package_type": "graph_collection", # 错误的类型
            "entry_point": "file.json",
            "format_version": "1.0"
        }
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("data/file.json", "{}")
        
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("wrong_type.hevno.zip", zip_buffer.getvalue(), "application/zip")}
        )
        assert import_resp.status_code == 400
        assert "Invalid package type" in import_resp.json()["detail"]

    def test_import_conflicting_sandbox_id(
        self, test_client: TestClient, linear_collection: GraphCollection
    ):
        """测试当导入的沙盒 ID 已存在时，应返回 409 Conflict。"""
        # 1. 先创建一个沙盒
        create_resp = test_client.post(
            "/api/sandboxes",
            json={"name": "Existing Sandbox", "graph_collection": linear_collection.model_dump()}
        )
        assert create_resp.status_code == 201
        sandbox_id = create_resp.json()["id"]

        # 2. 构造一个具有相同 ID 的导出包
        # (我们手动构造，而不是真的去导出，这样更快)
        sandbox = {"id": sandbox_id, "name": "Duplicate Sandbox", "head_snapshot_id": None}
        manifest = {"package_type": "sandbox_archive", "entry_point": "sandbox.json"}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("data/sandbox.json", json.dumps(sandbox))
            # 为了通过验证，至少需要一个快照
            snapshot = {"id": str(uuid4()), "sandbox_id": sandbox_id, "graph_collection": linear_collection.model_dump()}
            zf.writestr(f"data/snapshots/{snapshot['id']}.json", json.dumps(snapshot))

        # 3. 尝试导入
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("conflict.hevno.zip", zip_buffer.getvalue(), "application/zip")}
        )
        assert import_resp.status_code == 409
        assert "already exists" in import_resp.json()["detail"]