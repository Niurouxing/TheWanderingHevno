# plugins/core_engine/tests/test_editor_api.py

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any
from uuid import UUID

# 从平台核心契约导入
from backend.core.contracts import Container

# 从依赖插件的契约导入数据模型和接口
from plugins.core_engine.contracts import (
    GraphCollection,
    SnapshotStoreInterface,
    Sandbox,
    StateSnapshot,
    GenericNode,
    RuntimeInstruction
)

# 将此文件中的所有测试标记为 e2e
pytestmark = pytest.mark.e2e

@pytest.fixture
def setup_sandbox(
    test_client: TestClient,
    linear_collection: GraphCollection,
) -> Sandbox:
    """
    一个用于 Editor API 测试的 Fixture。
    它会创建一个初始的沙盒和创世快照，并将它们放入应用的状态存储中，
    以便 API 端点可以找到它们。
    """
    # 获取 DI 容器和核心服务
    container: Container = test_client.app.state.container
    sandbox_store: Dict[UUID, Sandbox] = container.resolve("sandbox_store")
    snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

    # 清理旧数据以保证测试隔离
    sandbox_store.clear()
    snapshot_store.clear()

    # 创建沙盒
    create_request_body = {
        "name": "Editor API Test Sandbox",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump()},
            "initial_moment": {"player_name": "EditorTester"}
        }
    }
    response = test_client.post("/api/sandboxes", json=create_request_body)
    assert response.status_code == 201
    
    sandbox_data = response.json()
    sandbox_id = UUID(sandbox_data["id"])
    
    # 从存储中返回完整的 Sandbox 对象以供测试使用
    sandbox = sandbox_store.get(sandbox_id)
    yield sandbox

    # 测试后清理
    sandbox_store.clear()
    snapshot_store.clear()


class TestScopeAPI:
    """测试顶层作用域 (definition, lore, moment) 的 API。"""

    def test_get_scope_content(self, test_client: TestClient, setup_sandbox: Sandbox):
        sandbox_id = setup_sandbox.id
        
        # 测试获取 definition
        res_def = test_client.get(f"/api/sandboxes/{sandbox_id}/definition")
        assert res_def.status_code == 200
        assert "initial_lore" in res_def.json()

        # 测试获取 lore
        res_lore = test_client.get(f"/api/sandboxes/{sandbox_id}/lore")
        assert res_lore.status_code == 200
        assert "graphs" in res_lore.json()
        
        # 测试获取 moment
        res_moment = test_client.get(f"/api/sandboxes/{sandbox_id}/moment")
        assert res_moment.status_code == 200
        assert res_moment.json() == {"player_name": "EditorTester"}

    def test_replace_scope_content(self, test_client: TestClient, setup_sandbox: Sandbox):
        sandbox_id = setup_sandbox.id
        original_snapshot_id = setup_sandbox.head_snapshot_id
        
        # 1. 替换 definition (不应创建新快照)
        new_def = {"new_key": "def_val"}
        res_put_def = test_client.put(f"/api/sandboxes/{sandbox_id}/definition", json=new_def)
        assert res_put_def.status_code == 200
        assert res_put_def.json()["definition"] == new_def
        assert UUID(res_put_def.json()["head_snapshot_id"]) == original_snapshot_id

        # 2. 替换 lore (不应创建新快照)
        new_lore = {"new_key": "lore_val"}
        res_put_lore = test_client.put(f"/api/sandboxes/{sandbox_id}/lore", json=new_lore)
        assert res_put_lore.status_code == 200
        assert res_put_lore.json()["lore"] == new_lore
        assert UUID(res_put_lore.json()["head_snapshot_id"]) == original_snapshot_id
        
        # 3. 替换 moment (必须创建新快照)
        new_moment = {"new_key": "moment_val"}
        res_put_moment = test_client.put(f"/api/sandboxes/{sandbox_id}/moment", json=new_moment)
        assert res_put_moment.status_code == 200
        
        updated_sandbox_data = res_put_moment.json()
        new_snapshot_id = UUID(updated_sandbox_data["head_snapshot_id"])
        assert new_snapshot_id != original_snapshot_id

        # 验证新快照的内容
        res_get_moment = test_client.get(f"/api/sandboxes/{sandbox_id}/moment")
        assert res_get_moment.json() == new_moment

    def test_patch_scope_content(self, test_client: TestClient, setup_sandbox: Sandbox):
        sandbox_id = setup_sandbox.id
        original_snapshot_id = setup_sandbox.head_snapshot_id
        
        # 1. Patch lore (不应创建新快照)
        patch_lore_op = [{"op": "add", "path": "/graphs/new_graph", "value": {"nodes": []}}]
        res_patch_lore = test_client.patch(f"/api/sandboxes/{sandbox_id}/lore", json=patch_lore_op)
        assert res_patch_lore.status_code == 200, res_patch_lore.text
        assert "new_graph" in res_patch_lore.json()["lore"]["graphs"]
        assert UUID(res_patch_lore.json()["head_snapshot_id"]) == original_snapshot_id

        # 2. Patch moment (必须创建新快照)
        patch_moment_op = [{"op": "add", "path": "/new_status", "value": "patched"}]
        res_patch_moment = test_client.patch(f"/api/sandboxes/{sandbox_id}/moment", json=patch_moment_op)
        assert res_patch_moment.status_code == 200, res_patch_moment.text

        updated_sandbox_data = res_patch_moment.json()
        new_snapshot_id = UUID(updated_sandbox_data["head_snapshot_id"])
        assert new_snapshot_id != original_snapshot_id

        # 验证新快照的内容
        res_get_moment = test_client.get(f"/api/sandboxes/{sandbox_id}/moment")
        assert res_get_moment.json()["new_status"] == "patched"


class TestGraphNodeInstructionAPI:
    """
    测试对图、节点、指令的完整 CRUD API。
    使用 parametrize 来高效地测试 'lore' 和 'moment' 两种作用域。
    """
    def _prepare_moment_scope(self, test_client: TestClient, sandbox: Sandbox):
        """辅助函数：确保 moment 作用域包含一个可供操作的图。"""
        main_graph_from_lore = sandbox.lore.get("graphs", {}).get("main")
        assert main_graph_from_lore is not None, "Fixture 'linear_collection' is missing 'main' graph."
        
        # 将 'main' 图从 lore 复制到 moment
        response = test_client.put(
            f"/api/sandboxes/{sandbox.id}/moment/graphs/main",
            json=main_graph_from_lore
        )
        response.raise_for_status() # 确保此操作成功


    @pytest.mark.parametrize("scope", ["lore", "moment"])
    def test_graph_crud(self, test_client: TestClient, setup_sandbox: Sandbox, scope: str):
        sandbox_id = setup_sandbox.id
        base_url = f"/api/sandboxes/{sandbox_id}/{scope}/graphs"
        
        # 1. 创建 (UPSERT)
        graph_def = {"nodes": [{"id": "test_node", "run": []}]}
        res_put = test_client.put(f"{base_url}/test_graph", json=graph_def)
        assert res_put.status_code == 200, res_put.text

        # 2. 读取 (单个图)
        res_get = test_client.get(f"{base_url}/test_graph")
        assert res_get.status_code == 200, res_get.text
        assert res_get.json()["nodes"][0]["id"] == "test_node"

        # 3. 删除
        res_del = test_client.delete(f"{base_url}/test_graph")
        assert res_del.status_code == 200, res_del.text

        # 4. 验证删除
        res_get_after = test_client.get(f"{base_url}/test_graph")
        assert res_get_after.status_code == 404

    @pytest.mark.parametrize("scope", ["lore", "moment"])
    def test_node_crud_and_reorder(self, test_client: TestClient, setup_sandbox: Sandbox, scope: str):
        sandbox_id = setup_sandbox.id
        
        # 【修复 3】如果测试 moment, 先确保 moment 中有 main graph
        if scope == "moment":
            self._prepare_moment_scope(test_client, setup_sandbox)

        base_url = f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main/nodes"
        
        # 1. 添加节点
        node_data = GenericNode(id="new_node", run=[]).model_dump()
        res_add = test_client.post(base_url, json=node_data)
        assert res_add.status_code == 200, res_add.text

        # 2. 更新节点
        updated_node_data = GenericNode(id="new_node", run=[], metadata={"updated": True}).model_dump()
        res_update = test_client.put(f"{base_url}/new_node", json=updated_node_data)
        assert res_update.status_code == 200, res_update.text
        
        # 3. 重新排序节点
        graph_res = test_client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        assert graph_res.status_code == 200, graph_res.text
        nodes = graph_res.json()["nodes"]
        node_ids = [n["id"] for n in nodes]
        assert "new_node" in node_ids
        
        reordered_ids = list(reversed(node_ids))
        res_reorder = test_client.post(f"{base_url}:reorder", json={"node_ids": reordered_ids})
        assert res_reorder.status_code == 200, res_reorder.text

        # 4. 删除节点
        res_del = test_client.delete(f"{base_url}/new_node")
        assert res_del.status_code == 200, res_del.text
        
        # 5. 验证状态
        final_graph_res = test_client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        final_node_ids = [n["id"] for n in final_graph_res.json()["nodes"]]
        assert "new_node" not in final_node_ids
        assert len(final_node_ids) == len(reordered_ids) - 1

    @pytest.mark.parametrize("scope", ["lore", "moment"])
    def test_instruction_crud(self, test_client: TestClient, setup_sandbox: Sandbox, scope: str):
        sandbox_id = setup_sandbox.id
        
        # 【修复 3】如果测试 moment, 先确保 moment 中有 main graph
        if scope == "moment":
            self._prepare_moment_scope(test_client, setup_sandbox)
            
        base_url = f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main/nodes/A/runtimes"

        # 1. 添加指令
        instr_data = RuntimeInstruction(runtime="system.test", config={"val": 1}).model_dump()
        res_add = test_client.post(base_url, json=instr_data)
        assert res_add.status_code == 200, res_add.text
        
        graph_res = test_client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        assert graph_res.status_code == 200, graph_res.text
        node_A = next(n for n in graph_res.json()["nodes"] if n["id"] == "A")
        assert len(node_A["run"]) == 2

        # 2. 更新指令
        updated_instr_data = RuntimeInstruction(runtime="system.test.updated", config={"val": 2}).model_dump()
        res_update = test_client.put(f"{base_url}/1", json=updated_instr_data)
        assert res_update.status_code == 200, res_update.text
        
        # 3. 删除指令
        res_del = test_client.delete(f"{base_url}/1")
        assert res_del.status_code == 200, res_del.text
        
        # 4. 验证状态
        final_graph_res = test_client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        final_node_A = next(n for n in final_graph_res.json()["nodes"] if n["id"] == "A")
        assert len(final_node_A["run"]) == 1
        assert final_node_A["run"][0]["runtime"] == "system.io.input"

class TestEditorApiErrorHandling:
    """测试编辑器API的各种错误处理情况。"""

    def test_operation_on_nonexistent_sandbox(self, test_client: TestClient):
        nonexistent_id = "11111111-1111-1111-1111-111111111111"
        res = test_client.get(f"/api/sandboxes/{nonexistent_id}/lore")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_operation_on_nonexistent_graph(self, test_client: TestClient, setup_sandbox: Sandbox):
        # 【修复 2 的断言】现在应该返回 404
        res = test_client.get(f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/nonexistent_graph")
        assert res.status_code == 404
        
        res_del = test_client.delete(f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/nonexistent_graph")
        assert res_del.status_code == 404

    def test_operation_on_nonexistent_node(self, test_client: TestClient, setup_sandbox: Sandbox):
        url = f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/main/nodes/nonexistent_node"
        res = test_client.delete(url)
        assert res.status_code == 404

    def test_add_node_with_duplicate_id(self, test_client: TestClient, setup_sandbox: Sandbox):
        url = f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/main/nodes"
        # 节点 'A' 已经存在
        node_data = GenericNode(id="A", run=[]).model_dump()
        res = test_client.post(url, json=node_data)
        assert res.status_code == 409 # Conflict
        assert "already exists" in res.json()["detail"]

    def test_invalid_json_patch(self, test_client: TestClient, setup_sandbox: Sandbox):
        url = f"/api/sandboxes/{setup_sandbox.id}/lore"
        invalid_patch = [{"op": "invalid_op", "path": "/test"}]
        res = test_client.patch(url, json=invalid_patch)
        assert res.status_code == 422 # Unprocessable Entity
        assert "Invalid JSON-Patch" in res.json()["detail"]