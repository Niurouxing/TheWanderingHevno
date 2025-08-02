# tests/test_04_api_e2e.py
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from backend.core.models import GraphCollection


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
        assert response.status_code == 200, response.text
        sandbox_data = response.json()
        sandbox_id = sandbox_data["id"]
        genesis_snapshot_id = sandbox_data["head_snapshot_id"]
        assert sandbox_id is not None
        assert genesis_snapshot_id is not None

        # 2. 执行一步
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "test"})
        assert response.status_code == 200, response.text
        step1_snapshot_data = response.json()
        step1_snapshot_id = step1_snapshot_data["id"]

        assert "plugin_metadata" in step1_snapshot_data["world_state"]
        assert "example_logger" in step1_snapshot_data["world_state"]["plugin_metadata"]
        assert "This snapshot was processed" in step1_snapshot_data["world_state"]["plugin_metadata"]["example_logger"]["message"]
        
        # 验证图执行成功，并且最终节点 'C' 存在于输出中
        run_output = step1_snapshot_data.get("run_output", {})
        assert "C" in run_output
        
        # 【关键修改】验证 'C' 节点的输出是来自 MockLLMService
        assert "llm_output" in run_output["C"]
        assert run_output["C"]["llm_output"].startswith("[MOCK RESPONSE for mock/model]")

        # 3. 获取历史记录
        response = test_client.get(f"/api/sandboxes/{sandbox_id}/history")
        assert response.status_code == 200, response.text
        history = response.json()
        assert len(history) == 2, "History should contain the genesis and the first step snapshots."

        # 4. 回滚到创世快照
        response = test_client.put(
            f"/api/sandboxes/{sandbox_id}/revert",
            params={"snapshot_id": genesis_snapshot_id}
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"message": f"Sandbox reverted to snapshot {genesis_snapshot_id}"}

        # 5. 再次执行一步，验证父快照是创世快照
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={"user_message": "re-test"})
        assert response.status_code == 200, response.text
        step2_snapshot_data = response.json()
        assert step2_snapshot_data["parent_snapshot_id"] == genesis_snapshot_id


@pytest.mark.e2e
class TestApiErrorHandling:
    """测试 API 在各种错误情况下的响应。"""

    def test_create_sandbox_with_invalid_graph(self, test_client: TestClient, invalid_graph_no_main: dict):
        response = test_client.post(
            "/api/sandboxes",
            json={
                "name": "Invalid Graph Test",
                "graph_collection": invalid_graph_no_main
            }
        )
        assert response.status_code == 422, "Should fail with Unprocessable Entity for invalid graph structure"
        
        error_data = response.json()
        print("Received error data:", error_data) # <--- 增加这行来调试，确认结构

        error_detail = error_data["detail"][0]
        
        # 【最终修正】直接检查 `msg` 字段，这是处理 RootModel 验证错误的更可靠方法
        assert "A 'main' graph must be defined" in error_detail["msg"]
        
        # 我们仍然可以检查错误类型和位置
        assert error_detail["type"] == "value_error"
        # 对于 RootModel，位置可能只指向模型本身，而不是 'root' 字段
        assert error_detail["loc"] == ["body", "graph_collection"]

    def test_operations_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = uuid4()
        
        # Step
        response = test_client.post(f"/api/sandboxes/{nonexistent_id}/step", json={})
        assert response.status_code == 404
        
        # History
        response = test_client.get(f"/api/sandboxes/{nonexistent_id}/history")
        assert response.status_code == 404

        # Revert
        response = test_client.put(f"/api/sandboxes/{nonexistent_id}/revert", params={"snapshot_id": uuid4()})
        assert response.status_code == 404


@pytest.mark.e2e
class TestApiWithComplexGraphs:
    """测试涉及更复杂图逻辑（如子图调用）的 API 端点。"""

    def test_e2e_with_subgraph_call(self, test_client: TestClient, subgraph_call_collection: GraphCollection):
        """
        通过 API 端到端测试一个包含 system.call 的图。
        """
        # 1. 创建沙盒
        response = test_client.post(
            "/api/sandboxes",
            json={
                "name": "E2E Subgraph Test",
                "graph_collection": subgraph_call_collection.model_dump(),
                "initial_state": {"global_setting": "Omega"}
            }
        )
        assert response.status_code == 200, response.text
        sandbox_id = response.json()["id"]

        # 2. 执行一步
        response = test_client.post(f"/api/sandboxes/{sandbox_id}/step", json={})
        assert response.status_code == 200, response.text
        
        # 3. 验证结果
        snapshot_data = response.json()
        run_output = snapshot_data.get("run_output", {})
        
        # 断言调用节点和子图的输出结构
        assert "main_caller" in run_output
        subgraph_output = run_output["main_caller"]["output"]
        assert "processor" in subgraph_output
        
        # 验证子图内部节点的最终输出值
        processor_output = subgraph_output["processor"]["output"]
        expected_str = "Processed: Hello from main with world state: Omega"
        assert processor_output == expected_str