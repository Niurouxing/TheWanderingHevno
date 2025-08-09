# plugins/core_engine/tests/test_editor_api.py

import pytest
from httpx import AsyncClient
from typing import Dict, Any, List
from uuid import UUID

from plugins.core_engine.contracts import (
    Sandbox,
    GenericNode,
    RuntimeInstruction,
    GraphCollection
)

# 标记此文件中的所有测试都是端到端(e2e)测试
pytestmark = pytest.mark.e2e

@pytest.fixture
async def setup_sandbox(client: AsyncClient, linear_collection: GraphCollection) -> Sandbox:
    """
    【E2E Fixture】
    使用 API 创建一个初始沙盒，为每个测试函数提供一个干净、隔离的环境。
    这确保了测试是针对一个真实的、通过API管理的状态进行的。
    """
    # 1. Arrange: 通过 API 创建沙盒
    create_request_body = {
        "name": "Editor API Test Sandbox",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump(mode='json')},
            "initial_moment": {"player_name": "EditorTester"}
        }
    }
    response = await client.post("/api/sandboxes", json=create_request_body)
    assert response.status_code == 201, f"Failed to create sandbox for E2E test: {response.text}"
    
    # 将返回的 JSON 数据解析为 Sandbox Pydantic 模型，以便在测试中进行类型安全的操作
    sandbox = Sandbox.model_validate(response.json())
    
    yield sandbox

    # 2. Teardown: 测试结束后，通过 API 删除沙盒以确保隔离性
    await client.delete(f"/api/sandboxes/{sandbox.id}")


class TestScopeAPI:
    """【E2E】测试顶层作用域 (definition, lore, moment) 的 API。"""

    async def test_get_scope_content(self, client: AsyncClient, setup_sandbox: Sandbox):
        sandbox_id = setup_sandbox.id
        
        # 测试获取 definition
        res_def = await client.get(f"/api/sandboxes/{sandbox_id}/definition")
        assert res_def.status_code == 200
        assert "initial_lore" in res_def.json()

        # 测试获取 lore
        res_lore = await client.get(f"/api/sandboxes/{sandbox_id}/lore")
        assert res_lore.status_code == 200
        assert "graphs" in res_lore.json()
        
        # 测试获取 moment
        res_moment = await client.get(f"/api/sandboxes/{sandbox_id}/moment")
        assert res_moment.status_code == 200
        assert res_moment.json() == {"player_name": "EditorTester"}

    async def test_replace_and_patch_scopes_and_verify_snapshot_creation(
        self, client: AsyncClient, setup_sandbox: Sandbox
    ):
        """
        【关键E2E测试】验证对不同作用域的修改是否遵循正确的快照创建规则。
        """
        sandbox_id = setup_sandbox.id
        original_snapshot_id = setup_sandbox.head_snapshot_id
        
        # --- 1. 修改 lore (不应创建新快照) ---
        new_lore = {"new_key": "lore_val"}
        res_put_lore = await client.put(f"/api/sandboxes/{sandbox_id}/lore", json=new_lore)
        assert res_put_lore.status_code == 200
        assert res_put_lore.json()["lore"] == new_lore
        assert UUID(res_put_lore.json()["head_snapshot_id"]) == original_snapshot_id, \
            "Updating lore should NOT create a new snapshot"

        # --- 2. 修改 definition (不应创建新快照) ---
        patch_def_op = [{"op": "add", "path": "/new_setting", "value": "enabled"}]
        res_patch_def = await client.patch(f"/api/sandboxes/{sandbox_id}/definition", json=patch_def_op)
        assert res_patch_def.status_code == 200
        assert res_patch_def.json()["definition"]["new_setting"] == "enabled"
        assert UUID(res_patch_def.json()["head_snapshot_id"]) == original_snapshot_id, \
            "Updating definition should NOT create a new snapshot"
        
        # --- 3. 修改 moment (必须创建新快照) ---
        patch_moment_op = [{"op": "add", "path": "/new_status", "value": "patched"}]
        res_patch_moment = await client.patch(f"/api/sandboxes/{sandbox_id}/moment", json=patch_moment_op)
        assert res_patch_moment.status_code == 200
        
        updated_sandbox_data = res_patch_moment.json()
        new_snapshot_id = UUID(updated_sandbox_data["head_snapshot_id"])
        assert new_snapshot_id != original_snapshot_id, "Updating moment MUST create a new snapshot"

        # 验证新快照的内容是否正确
        res_get_moment = await client.get(f"/api/sandboxes/{sandbox_id}/moment")
        assert res_get_moment.json()["new_status"] == "patched"


class TestGraphNodeInstructionAPI:
    """【E2E】测试对图、节点、指令的完整 CRUD API。"""

    async def _prepare_moment_scope(self, client: AsyncClient, sandbox: Sandbox):
        """辅助函数：确保 moment 作用域包含一个可供操作的图。"""
        main_graph_from_lore = sandbox.lore.get("graphs", {}).get("main")
        assert main_graph_from_lore is not None, "Fixture 'linear_collection' is missing 'main' graph."
        
        # 将 'main' 图从 lore 复制到 moment
        response = await client.put(
            f"/api/sandboxes/{sandbox.id}/moment/graphs/main",
            json=main_graph_from_lore
        )
        assert response.status_code == 200, "Failed to prepare moment scope for test"

    @pytest.mark.parametrize("scope", ["lore", "moment"])
    async def test_graph_crud(self, client: AsyncClient, setup_sandbox: Sandbox, scope: str):
        sandbox_id = setup_sandbox.id
        base_url = f"/api/sandboxes/{sandbox_id}/{scope}/graphs"
        
        # 为 moment 作用域做准备，否则它为空
        if scope == "moment":
            await self._prepare_moment_scope(client, setup_sandbox)
        
        # 1. 创建 (UPSERT)
        graph_def = {"nodes": [{"id": "test_node", "run": []}]}
        res_put = await client.put(f"{base_url}/test_graph", json=graph_def)
        assert res_put.status_code == 200

        # 2. 读取 (单个图)
        res_get = await client.get(f"{base_url}/test_graph")
        assert res_get.status_code == 200
        assert res_get.json()["nodes"][0]["id"] == "test_node"

        # 3. 删除
        res_del = await client.delete(f"{base_url}/test_graph")
        assert res_del.status_code == 204 # 验证返回了 204 No Content

        # 4. 验证删除
        res_get_after = await client.get(f"{base_url}/test_graph")
        assert res_get_after.status_code == 404

    @pytest.mark.parametrize("scope", ["lore", "moment"])
    async def test_node_crud_and_reorder(self, client: AsyncClient, setup_sandbox: Sandbox, scope: str):
        sandbox_id = setup_sandbox.id
        if scope == "moment": await self._prepare_moment_scope(client, setup_sandbox)
        base_url = f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main/nodes"
        
        # 1. 添加节点
        node_data = GenericNode(id="new_node", run=[]).model_dump(mode='json')
        res_add = await client.post(base_url, json=node_data)
        assert res_add.status_code == 201

        # 2. 更新节点
        updated_node_data = GenericNode(id="new_node", run=[], metadata={"updated": True}).model_dump(mode='json')
        res_update = await client.put(f"{base_url}/new_node", json=updated_node_data)
        assert res_update.status_code == 200
        
        # 3. 重新排序节点
        graph_res = await client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        node_ids = [n["id"] for n in graph_res.json()["nodes"]]
        reordered_ids = list(reversed(node_ids))
        res_reorder = await client.post(f"{base_url}:reorder", json={"node_ids": reordered_ids})
        assert res_reorder.status_code == 204

        # 4. 删除节点
        res_del = await client.delete(f"{base_url}/new_node")
        assert res_del.status_code == 204
        
        # 5. 验证状态
        final_graph_res = await client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        final_node_ids = [n["id"] for n in final_graph_res.json()["nodes"]]
        assert "new_node" not in final_node_ids
        assert len(final_node_ids) == len(reordered_ids) - 1

    @pytest.mark.parametrize("scope", ["lore", "moment"])
    async def test_instruction_crud(self, client: AsyncClient, setup_sandbox: Sandbox, scope: str):
        sandbox_id = setup_sandbox.id
        if scope == "moment": await self._prepare_moment_scope(client, setup_sandbox)
        base_url = f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main/nodes/A/runtimes"

        # 1. 添加指令
        instr_data = RuntimeInstruction(runtime="system.test", config={"val": 1}).model_dump(mode='json')
        res_add = await client.post(base_url, json=instr_data)
        assert res_add.status_code == 201
        
        # 2. 验证指令已添加
        graph_res = await client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        node_A = next(n for n in graph_res.json()["nodes"] if n["id"] == "A")
        assert len(node_A["run"]) == 2 # 原始1条 + 新增1条

        # 3. 更新指令 (更新刚刚添加的第2条，索引为1)
        updated_instr_data = RuntimeInstruction(runtime="system.test.updated", config={"val": 2}).model_dump(mode='json')
        res_update = await client.put(f"{base_url}/1", json=updated_instr_data)
        assert res_update.status_code == 200
        
        # 4. 删除指令
        res_del = await client.delete(f"{base_url}/1")
        assert res_del.status_code == 204
        
        # 5. 验证最终状态
        final_graph_res = await client.get(f"/api/sandboxes/{sandbox_id}/{scope}/graphs/main")
        final_node_A = next(n for n in final_graph_res.json()["nodes"] if n["id"] == "A")
        assert len(final_node_A["run"]) == 1
        assert final_node_A["run"][0]["runtime"] == "system.io.input"


class TestEditorApiErrorHandling:
    """【E2E】测试编辑器API的各种错误处理情况。"""

    async def test_operation_on_nonexistent_sandbox(self, client: AsyncClient):
        nonexistent_id = "11111111-1111-1111-1111-111111111111"
        res = await client.get(f"/api/sandboxes/{nonexistent_id}/lore")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    async def test_operation_on_nonexistent_graph(self, client: AsyncClient, setup_sandbox: Sandbox):
        res = await client.get(f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/nonexistent_graph")
        assert res.status_code == 404
        
        res_del = await client.delete(f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/nonexistent_graph")
        assert res_del.status_code == 404

    async def test_operation_on_nonexistent_node(self, client: AsyncClient, setup_sandbox: Sandbox):
        url = f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/main/nodes/nonexistent_node"
        res = await client.delete(url)
        assert res.status_code == 404

    async def test_add_node_with_duplicate_id(self, client: AsyncClient, setup_sandbox: Sandbox):
        url = f"/api/sandboxes/{setup_sandbox.id}/lore/graphs/main/nodes"
        # 节点 'A' 已经存在于 linear_collection 中
        node_data = GenericNode(id="A", run=[]).model_dump(mode='json')
        res = await client.post(url, json=node_data)
        assert res.status_code == 409 # Conflict
        assert "already exists" in res.json()["detail"]

    async def test_invalid_json_patch(self, client: AsyncClient, setup_sandbox: Sandbox):
        url = f"/api/sandboxes/{setup_sandbox.id}/lore"
        invalid_patch = [{"op": "invalid_op", "path": "/test"}]
        res = await client.patch(url, json=invalid_patch)
        assert res.status_code == 422 # Unprocessable Entity
        assert "Invalid JSON-Patch" in res.json()["detail"]