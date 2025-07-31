# tests/test_04_api_e2e.py
import pytest
from fastapi.testclient import TestClient
from uuid import UUID, uuid4

from backend.models import GraphCollection

# ---------------------------------------------------------------------------
# Section 1: Sandbox Lifecycle E2E Tests
# ---------------------------------------------------------------------------

class TestApiSandboxLifecycle:
    """测试沙盒从创建、执行、查询到回滚的完整生命周期。"""
    
    def test_full_lifecycle(self, test_client: TestClient, linear_collection: GraphCollection):
        """
        一个完整的端到端 happy path 测试。
        这个测试的逻辑基本不变，因为它不关心图内部的实现，只关心 API 交互。
        """
        # --- 1. 创建沙盒 ---
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "E2E Test Sandbox"},
            json={
                "graph_collection": linear_collection.model_dump(),
                "initial_state": {"player": "Humphrey"} 
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
            json={"user_message": "A test input"} # Body 现在是 user_input
        )
        assert response.status_code == 200
        step1_snapshot_data = response.json()
        
        assert step1_snapshot_data["id"] != genesis_snapshot_id
        assert step1_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id
        step1_snapshot_id = step1_snapshot_data["id"]
        
        # 验证执行结果是否符合预期（可选，但推荐）
        run_output = step1_snapshot_data.get("run_output", {})
        assert "C" in run_output
        assert "LLM_RESPONSE_FOR" in run_output["C"]["llm_output"]

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
            json={"user_message": "A different input"}
        )
        assert response.status_code == 200
        step2_snapshot_data = response.json()
        
        # 验证新快照的父节点是回滚后的创世快照
        assert step2_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id


# ---------------------------------------------------------------------------
# Section 2: API Error Handling E2E Tests
# ---------------------------------------------------------------------------

class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        """
        关键修改：测试当图定义无效时（如缺少 main），API 返回 422 错误。
        """
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid Sandbox"},
            json={
                "graph_collection": invalid_graph_no_main,
                "initial_state": {}
            }
        )

        assert response.status_code == 422 
        error_data = response.json()
        
        assert "detail" in error_data
        assert isinstance(error_data["detail"], list) and len(error_data["detail"]) > 0

        first_error = error_data["detail"][0]
        assert first_error["type"] == "value_error"
        assert "A 'main' graph must be defined as the entry point." in first_error["msg"]
        
        # --- 关键修复 ---
        # 对于 RootModel，FastAPI/Pydantic v2 的错误路径指向模型本身，而不是其内部的 'root' 字段。
        # 所以正确的路径是 `['body', 'graph_collection']`。
        # 你的 `@field_validator('root')` 是正确的 Pydantic 内部用法，但外部错误报告路径不同。
        assert first_error["loc"] == ["body", "graph_collection"]

    def test_create_sandbox_with_invalid_pydantic_payload(self, test_client: TestClient):
        """测试一个在 Pydantic 层就无法解析的请求体。"""
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Invalid Payload"},
            json={
                "graph_collection": "this-should-be-a-dict", # 错误类型
                "initial_state": "this-should-be-a-dict"
            }
        )

        assert response.status_code == 422
        error_data = response.json()["detail"]
        assert any("Input should be a valid dictionary" in e["msg"] for e in error_data)
        assert any(["body", "graph_collection"] == e["loc"] for e in error_data)

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        """测试对不存在的沙盒进行操作。"""
        nonexistent_id = uuid4()
        
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        assert response.json()["detail"] == "Sandbox not found."
        
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        # GET 历史通常返回空列表而不是 404，这是一种常见实践
        assert response.status_code == 200
        assert response.json() == []

        response = test_client.put(
            f"/api/sandboxes/{nonexistent_id}/revert",
            params={"snapshot_id": uuid4()}
        )
        assert response.status_code == 404
        assert "Sandbox or Snapshot not found" in response.json()["detail"]
    
    def test_revert_to_nonexistent_snapshot(self, test_client: TestClient, linear_collection: GraphCollection):
        """测试回滚到一个不存在的快照。"""
        # 先创建一个有效的沙盒
        response = test_client.post(
            "/api/sandboxes",
            params={"name": "Revert Test"},
            json={"graph_collection": linear_collection.model_dump()}
        )
        assert response.status_code == 200
        sandbox_id = response.json()["id"]
        
        nonexistent_id = uuid4()
        
        # 尝试回滚
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": nonexistent_id}
        )
        assert response.status_code == 404
        assert "Sandbox or Snapshot not found" in response.json()["detail"]