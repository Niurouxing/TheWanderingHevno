# plugins/core_api/tests/test_api_e2e.py 

import pytest
import zipfile
import io
import json
from fastapi.testclient import TestClient
from uuid import uuid4, UUID
import base64
from PIL import Image, PngImagePlugin 
from pydantic import BaseModel 
import logging
logger = logging.getLogger(__name__)

# 从平台核心契约导入
from backend.core.contracts import Container

# 从依赖插件的契约导入数据模型和接口
from plugins.core_engine.contracts import GraphCollection, SnapshotStoreInterface, Sandbox, StateSnapshot
from plugins.core_persistence.contracts import PersistenceServiceInterface


def create_test_png_package(manifest_dict: dict, data_files: dict) -> bytes:
    """一个辅助函数，用于为测试创建嵌入了zTXt数据的PNG包。"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("manifest.json", json.dumps(manifest_dict))
        for name, content_model in data_files.items():
            zf.writestr(f"data/{name}", content_model.model_dump_json())
    zip_bytes = zip_buffer.getvalue()
    encoded_data = base64.b64encode(zip_bytes).decode('ascii')
    image = Image.new('RGBA', (1, 1))
    png_info_obj = PngImagePlugin.PngInfo()
    png_info_obj.add_text("hevno:data", encoded_data)
    png_buffer = io.BytesIO()
    image.save(png_buffer, "PNG", pnginfo=png_info_obj)
    return png_buffer.getvalue()


@pytest.mark.e2e
class TestApiSandboxLifecycle:
    """【已重构】测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        # --- 1. 创建沙盒 ---
        create_request_body = {
            "name": "E2E Lifecycle Test",
            "definition": {
                "initial_lore": {
                    "graphs": linear_collection.model_dump()
                },
                "initial_moment": {
                    "player_name": "Tester"
                }
            }
        }
        response = test_client.post("/api/sandboxes", json=create_request_body)
        assert response.status_code == 201, response.text
        sandbox_data = response.json()
        sandbox_id = sandbox_data["id"]
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        assert sandbox_data["name"] == "E2E Lifecycle Test"
        assert "graphs" in sandbox_data["lore"]

        # --- 2. 执行一步 ---
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "test"})
        assert response.status_code == 200, response.text
        
        updated_sandbox_data = response.json()
        step1_snapshot_id = updated_sandbox_data["head_snapshot_id"]
        assert step1_snapshot_id != genesis_snapshot_id

        container: Container = test_client.app.state.container
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        step1_snapshot = snapshot_store.get(UUID(step1_snapshot_id))
        assert step1_snapshot is not None
        
        run_output = step1_snapshot.run_output
        assert "C" in run_output
        assert run_output["C"]["llm_output"].startswith("[MOCK RESPONSE for mock/model]")

        # --- 3. 获取历史记录 ---
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200, response.text
        history = response.json()
        assert len(history) == 2

        # --- 4. 回滚到创世快照 ---
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            json={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200, response.text
        
        # 验证回滚结果
        sandbox_store: Dict[UUID, Sandbox] = container.resolve("sandbox_store")
        final_sandbox_state = sandbox_store.get(UUID(sandbox_id))
        assert final_sandbox_state.head_snapshot_id == UUID(genesis_snapshot_id)

@pytest.mark.e2e
class TestSystemReportAPI:
    def test_get_system_report(self, test_client: TestClient):
        response = test_client.get("/api/system/report")
        assert response.status_code == 200, response.text
        report = response.json()
        assert "llm_providers" in report
        assert isinstance(report["llm_providers"], list)
        gemini_provider_report = next((p for p in report["llm_providers"] if p["name"] == "gemini"), None)
        assert gemini_provider_report is not None

@pytest.mark.e2e
class TestApiErrorHandling:
    def test_create_sandbox_with_invalid_definition(self, test_client: TestClient):
        response = test_client.post(
            "/api/sandboxes",
            json={"name": "Invalid Def", "definition": {"initial_moment": {}}}
        )
        assert response.status_code == 422, response.text
        error_detail = response.json()["detail"][0]
        assert "Definition must contain 'initial_lore' and 'initial_moment' keys" in error_detail["msg"]

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            json={
                "name": "Invalid Graph",
                "definition": {
                    "initial_lore": {"graphs": invalid_graph_no_main},
                    "initial_moment": {}
                }
            }
        )
        assert response.status_code == 201, response.text
        
        sandbox_id = response.json()["id"]
        step_response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        
        assert step_response.status_code == 500, step_response.text
        error_detail = step_response.json()["detail"]
        assert "Invalid graph structure" in error_detail
        assert "A 'main' graph must be defined" in error_detail

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = uuid4()
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404, response.text
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 404, response.text

@pytest.mark.e2e
class TestSandboxImportExport:
    """【已重构】专门测试沙盒导入/导出 API 的类。"""

    def test_sandbox_export_import_roundtrip(
        self, test_client: TestClient, linear_collection: GraphCollection
    ):
        # --- 步骤 1 & 2: 创建、执行、导出 ---
        create_resp = test_client.post(
            "/api/sandboxes",
            json={
                "name": "Export-Test-Sandbox",
                "definition": {
                    "initial_lore": {"graphs": linear_collection.model_dump()},
                    "initial_moment": {}
                }
            }
        )
        assert create_resp.status_code == 201
        sandbox_id = create_resp.json()["id"]

        step_resp = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert step_resp.status_code == 200
        
        export_resp = test_client.get(f"/api/sandboxes/{sandbox_id}/export")
        assert export_resp.status_code == 200, export_resp.text
        assert export_resp.headers['content-type'] == 'image/png'
        
        png_bytes = export_resp.content
        
        # --- 步骤 3: 验证导出的PNG文件 ---
        image = Image.open(io.BytesIO(png_bytes))
        image.load()
        encoded_data = image.text.get('hevno:data')
        assert encoded_data is not None
        zip_data = base64.b64decode(encoded_data)
        
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
            filenames = zf.namelist()
            assert "data/sandbox.json" in filenames
            # 验证导出的 sandbox.json 包含新字段
            exported_sandbox_json = json.loads(zf.read("data/sandbox.json"))
            assert "definition" in exported_sandbox_json
            assert "lore" in exported_sandbox_json
            assert "graphs" in exported_sandbox_json["lore"]
            assert len([f for f in filenames if f.startswith("data/snapshots/")]) == 2
            
            # 验证导出的 snapshot.json 包含新字段
            snapshot_filename = next(f for f in filenames if f.startswith("data/snapshots/"))
            exported_snapshot_json = json.loads(zf.read(snapshot_filename))
            assert "moment" in exported_snapshot_json
            assert "world_state" not in exported_snapshot_json # 验证旧字段已移除

        # --- 步骤 4: 清理状态 ---
        container: Container = test_client.app.state.container
        sandbox_store: dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        sandbox_store.clear()
        snapshot_store.clear()

        # --- 步骤 5: 导入PNG文件 ---
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("imported.png", png_bytes, "image/png")}
        )
        assert import_resp.status_code == 200, import_resp.text
        imported_sandbox = import_resp.json()
        
        # --- 步骤 6: 验证恢复的状态 ---
        assert imported_sandbox["id"] == sandbox_id
        assert imported_sandbox["name"] == "Export-Test-Sandbox"
        assert "definition" in imported_sandbox
        assert "lore" in imported_sandbox
        
        history_resp = test_client.get(f"/api/sandboxes/{imported_sandbox['id']}/history")
        assert history_resp.status_code == 200
        assert len(history_resp.json()) == 2

    def test_import_invalid_package_type(self, test_client: TestClient):
        """测试导入一个非沙盒类型的包应被拒绝。"""
        manifest = {
            "package_type": "graph_collection", # 错误的类型
            "entry_point": "file.json"
        }

        class EmptyModel(BaseModel):
            pass
        data_files = {"file.json": EmptyModel()}
        
        png_package = create_test_png_package(manifest, data_files)
        
        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("wrong_type.png", png_package, "image/png")}
        )
        assert import_resp.status_code == 400
        assert "Invalid package type" in import_resp.json()["detail"]

    def test_import_conflicting_sandbox_id(self, test_client: TestClient, linear_collection: GraphCollection):
        create_resp = test_client.post(
            "/api/sandboxes",
            json={
                "name": "Existing Sandbox",
                "definition": {
                    "initial_lore": {"graphs": linear_collection.model_dump()},
                    "initial_moment": {}
                }
            }
        )
        assert create_resp.status_code == 201
        sandbox_id = create_resp.json()["id"]

        sandbox_data = Sandbox(
            id=sandbox_id,
            name="Duplicate Sandbox",
            definition={"initial_lore": {}, "initial_moment": {}}
        )
        snapshot_data = StateSnapshot(sandbox_id=sandbox_id, moment={})
        manifest_data = {"package_type": "sandbox_archive", "entry_point": "sandbox.json"}
        data_files = {
            "sandbox.json": sandbox_data,
            f"snapshots/{snapshot_data.id}.json": snapshot_data
        }
        
        png_package = create_test_png_package(manifest_data, data_files)

        import_resp = test_client.post(
            "/api/sandboxes/import",
            files={"file": ("conflict.png", png_package, "image/png")}
        )
        
        assert import_resp.status_code == 409
        assert "already exists" in import_resp.json()["detail"]