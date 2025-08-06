# plugins/core_api/tests/test_api_e2e.py

import pytest
import zipfile
import io
import json
from fastapi.testclient import TestClient
from uuid import uuid4, UUID
import base64
from PIL import Image, PngImagePlugin 
import logging
logger = logging.getLogger(__name__)

# 从平台核心契约导入
from backend.core.contracts import Container

# 从依赖插件的契约导入数据模型和接口
from plugins.core_engine.contracts import GraphCollection, SnapshotStoreInterface
from plugins.core_persistence.contracts import PersistenceServiceInterface


def create_test_png_package(manifest_dict: dict, data_files: dict) -> bytes:
    """一个辅助函数，用于为测试创建嵌入了zTXt数据的PNG包。"""
    logger.debug(f"[TEST_HELPER] Creating test package. Manifest type: {manifest_dict.get('package_type')}")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("manifest.json", json.dumps(manifest_dict))
        for name, content in data_files.items():
            zf.writestr(f"data/{name}", json.dumps(content))
    zip_bytes = zip_buffer.getvalue()
    logger.debug(f"[TEST_HELPER] Created zip_bytes with size: {len(zip_bytes)}")

    encoded_data = base64.b64encode(zip_bytes).decode('ascii')

    image = Image.new('RGBA', (1, 1))
    
    png_info_obj = PngImagePlugin.PngInfo()
    png_info_obj.add_text("hevno:data", encoded_data)

    png_buffer = io.BytesIO()
    image.save(png_buffer, "PNG", pnginfo=png_info_obj)
    
    output_bytes = png_buffer.getvalue()
    logger.debug(f"[TEST_HELPER] Final test PNG size: {len(output_bytes)}")
    
    # 自我验证
    try:
        with Image.open(io.BytesIO(output_bytes)) as re_image:
            re_image.load()
            assert "hevno:data" in re_image.text, "[TEST_HELPER] FATAL: ztxt chunk not found in self-created package!"
            logger.debug("[TEST_HELPER] Self-verification successful. 'hevno:data' chunk is present.")
    except Exception as e:
        logger.error(f"[TEST_HELPER] Self-verification failed: {e}")
        pytest.fail(f"Test helper failed to create a valid PNG package: {e}")

    return output_bytes


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
    """专门测试沙盒导入/导出 API 的类 (已更新为PNG格式)。"""

    def test_sandbox_export_import_roundtrip(
        self, test_client: TestClient, linear_collection: GraphCollection
    ):
        # --- 步骤 1 & 2: 创建、执行、导出 ---
        create_resp = test_client.post(
            "/api/sandboxes",
            json={"name": "Export-Test-Sandbox", "graph_collection": linear_collection.model_dump()}
        )
        assert create_resp.status_code == 201
        sandbox_id = create_resp.json()["id"]

        step_resp = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert step_resp.status_code == 200
        
        export_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/export")
        assert export_resp.status_code == 200
        assert export_resp.headers['content-type'] == 'image/png'
        
        # --- 步骤 3: 验证导出的PNG文件 ---
        png_bytes = export_resp.content
        
        # 使用Pillow从PNG中提取ZIP数据
        image = Image.open(io.BytesIO(png_bytes))
        image.load()
        encoded_data = image.text.get('hevno:data')
        assert encoded_data is not None
        zip_data = base64.b64decode(encoded_data)
        assert zip_data is not None
        
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
            filenames = zf.namelist()
            assert "manifest.json" in filenames
            assert "data/sandbox.json" in filenames
            assert len([f for f in filenames if f.startswith("data/snapshots/")]) == 2
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["package_type"] == "sandbox_archive"

        # --- 步骤 4: 清理状态 ---
        container: Container = test_client.app.state.container
        sandbox_store: dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        sandbox_store.clear()
        snapshot_store.clear()

        # --- 步骤 5: 导入PNG文件 ---
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("imported.png", png_bytes, "image/png")} # <-- 使用正确的元数据
        )
        assert import_resp.status_code == 200, import_resp.text
        imported_sandbox = import_resp.json()
        
        # --- 步骤 6: 验证恢复的状态 ---
        assert imported_sandbox["id"] == sandbox_id
        assert imported_sandbox["name"] == "Export-Test-Sandbox"
        assert len(sandbox_store) == 1
        
        history_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert history_resp.status_code == 200
        assert len(history_resp.json()) == 2

    def test_import_invalid_package_type(self, test_client: TestClient):
        """测试导入一个非沙盒类型的包应被拒绝。"""
        manifest = {
            "package_type": "graph_collection", # 错误的类型
            "entry_point": "file.json"
        }
        data_files = {"file.json": {}}
        
        # 使用辅助函数创建包含错误 manifest 的合法PNG包
        png_package = create_test_png_package(manifest, data_files)
        
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("wrong_type.png", png_package, "image/png")}
        )
        assert import_resp.status_code == 400
        # 现在我们可以断言更深层次的业务逻辑错误了
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
        sandbox_data = {"id": sandbox_id, "name": "Duplicate Sandbox", "head_snapshot_id": None}
        manifest_data = {"package_type": "sandbox_archive", "entry_point": "sandbox.json"}
        snapshot_data = {"id": str(uuid4()), "sandbox_id": sandbox_id, "graph_collection": linear_collection.model_dump()}
        
        data_files = {
            "sandbox.json": sandbox_data,
            f"snapshots/{snapshot_data['id']}.json": snapshot_data
        }
        
        # 使用辅助函数创建包含冲突数据的合法PNG包
        png_package = create_test_png_package(manifest_data, data_files)

        # 3. 尝试导入
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("conflict.png", png_package, "image/png")}
        )
        
        # 现在断言应该通过了
        assert import_resp.status_code == 409
        assert "already exists" in import_resp.json()["detail"]