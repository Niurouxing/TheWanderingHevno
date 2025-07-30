# tests/test_04_api_e2e.py
import pytest
from fastapi.testclient import TestClient
from uuid import UUID

from backend.models import GraphCollection

class TestApiSandboxLifecycle:
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        # --- 1. 创建沙盒 ---
        # Body 现在需要是一个键，所以我们将它放入 json 参数中
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Test Sandbox"},
            # 将图数据作为 json 体
            json={
                "graph_collection": linear_collection.model_dump(),
                "initial_state": None 
            }
        )
        assert response.status_code == 200
        sandbox_data = response.json()
        assert sandbox_data["name"] == "E2E Test Sandbox"
        sandbox_id = sandbox_data["id"]
        
        assert sandbox_data["head_snapshot_id"] is not None
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]

        # --- 2. 执行一个步骤 ---
        response = test_client.post(
            f"/api/sandboxes/{sandbox_id}/step",
            json={"trigger": "start"}
        )
        assert response.status_code == 200
        step1_snapshot_data = response.json()
        
        assert step1_snapshot_data["id"] != genesis_snapshot_id
        assert step1_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id
        step1_snapshot_id = step1_snapshot_data["id"]

        # --- 3. 获取历史记录 ---
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200
        history = response.json()
        
        assert len(history) == 2
        history_ids = {item["id"] for item in history}
        assert genesis_snapshot_id in history_ids
        assert step1_snapshot_id in history_ids

        # --- 4. 回滚到创世快照 ---
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200
        assert response.json() == {"message": f"Sandbox reverted to snapshot {genesis_snapshot_id}"}
        
        # --- 5. 验证回滚后的状态 ---
        response = test_client.post(
            f"/api/sandboxes/{sandbox_id}/step",
            json={"trigger": "restart"}
        )
        assert response.status_code == 200
        step2_snapshot_data = response.json()
        
        assert step2_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id


class TestApiErrorHandling:
    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid Sandbox"},
            json={
                "graph_collection": invalid_graph_no_main
            }
        )
        assert response.status_code == 422
        # --- 修复：验证 Pydantic 标准错误格式 ---
        error_detail = response.json()["detail"][0]
        assert error_detail["type"] == "value_error"
        assert "A 'main' graph must be defined" in error_detail["msg"]
        # --- 修复结束 ---

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = UUID("00000000-0000-0000-0000-000000000000")
        
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 200
        assert response.json() == []

        response = test_client.put(
            f"/api/sandboxes/{nonexistent_id}/revert",
            params={"snapshot_id": nonexistent_id}
        )
        assert response.status_code == 404
    
    def test_revert_to_nonexistent_snapshot(self, test_client: TestClient, linear_collection: GraphCollection):
        # 先创建一个有效的沙盒
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Revert Test"},
            json={
                "graph_collection": linear_collection.model_dump()
            }
        )
        assert response.status_code == 200
        sandbox_id = response.json()["id"]
        
        nonexistent_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # 尝试回滚
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": nonexistent_id}
        )
        assert response.status_code == 404