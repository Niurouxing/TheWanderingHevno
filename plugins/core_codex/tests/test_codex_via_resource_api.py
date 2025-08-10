import pytest
from httpx import AsyncClient
from uuid import UUID


from plugins.core_engine.contracts import Sandbox, Mutation


# 标记为 e2e 测试
pytestmark = pytest.mark.e2e

@pytest.fixture
async def setup_sandbox(client: AsyncClient, linear_collection) -> Sandbox:
    """
    创建一个干净的沙盒用于测试。
    """
    create_request_body = {
        "name": "Codex API via Resource Test",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump(mode='json')},
            "initial_moment": {}
        }
    }
    response = await client.post("/api/sandboxes", json=create_request_body)
    # [修复] 笔误：状态码应该是 201
    assert response.status_code == 201, f"Failed to create sandbox: {response.text}"
    sandbox = Sandbox.model_validate(response.json())
    yield sandbox
    await client.delete(f"/api/sandboxes/{sandbox.id}")


class TestCodexViaResourceAPI:
    """
    测试通过统一的 /resource:* 端点来管理 Codex 数据。
    """

    # 直接在参数中请求 fixture 化的 API 辅助函数
    async def test_codex_full_crud_in_lore(self, client: AsyncClient, setup_sandbox: Sandbox, mutate_resource_api, query_resource_api):
        """
        验证在 lore 作用域中对 Codex 的完整 CRUD 操作。
        """
        sandbox_id = setup_sandbox.id
        codex_path = "lore/codices/world_history"
        entry_path = f"{codex_path}/entries/0"
        content_path = f"{entry_path}/content"

        # 1. CREATE
        codex_data = {
            "description": "世界的历史",
            "entries": [{"id": "creation", "content": "世界诞生于混沌之中。", "priority": 100}],
            "__hevno_type__": "hevno/codex"
        }
        create_mutations = [Mutation(type="UPSERT", path=codex_path, value=codex_data)]
        res_create = await mutate_resource_api(client, sandbox_id, create_mutations)
        assert res_create.status_code == 200

        # 2. READ
        query_results = await query_resource_api(client, sandbox_id, [codex_path, entry_path])
        assert query_results[codex_path]["description"] == "世界的历史"
        assert query_results[entry_path]["content"] == "世界诞生于混沌之中。"

        # 3. UPDATE
        update_mutations = [Mutation(type="UPSERT", path=content_path, value="世界由巨龙创造。")]
        res_update = await mutate_resource_api(client, sandbox_id, update_mutations)
        assert res_update.status_code == 200
        
        query_after_update = await query_resource_api(client, sandbox_id, [content_path])
        assert query_after_update[content_path] == "世界由巨龙创造。"

        # 4. DELETE
        delete_mutations = [Mutation(type="DELETE", path=codex_path)]
        res_delete = await mutate_resource_api(client, sandbox_id, delete_mutations)
        assert res_delete.status_code == 200

        query_after_delete = await query_resource_api(client, sandbox_id, [codex_path])
        assert query_after_delete[codex_path] is None

    # [修改] 直接在参数中请求 fixture 化的 API 辅助函数
    async def test_add_and_reorder_entries_in_moment(self, client: AsyncClient, setup_sandbox: Sandbox, mutate_resource_api, query_resource_api):
        """
        验证在 moment 作用域中添加和重排 Codex 条目。
        """
        sandbox_id = setup_sandbox.id
        codex_path = "moment/codices/temp_knowledge"
        entries_path = f"{codex_path}/entries"

        # 准备
        mutations_init = [Mutation(type="UPSERT", path=codex_path, value={"entries": []}, mutation_mode="DIRECT")]
        await mutate_resource_api(client, sandbox_id, mutations_init)

        # 1. APPEND
        entry1 = {"id": "fact_1", "content": "天是蓝的。"}
        entry2 = {"id": "fact_2", "content": "草是绿的。"}
        mutations_append = [
            Mutation(type="LIST_APPEND", path=entries_path, value=entry1, mutation_mode="DIRECT"),
            Mutation(type="LIST_APPEND", path=entries_path, value=entry2, mutation_mode="DIRECT")
        ]
        res_append = await mutate_resource_api(client, sandbox_id, mutations_append)
        assert res_append.status_code == 200

        query_res1 = await query_resource_api(client, sandbox_id, [entries_path])
        assert len(query_res1[entries_path]) == 2
        assert query_res1[entries_path][0]["id"] == "fact_1"

        # 2. REORDER
        reordered_entries = [entry2, entry1]
        mutations_reorder = [
            Mutation(type="UPSERT", path=entries_path, value=reordered_entries, mutation_mode="DIRECT")
        ]
        res_reorder = await mutate_resource_api(client, sandbox_id, mutations_reorder)
        assert res_reorder.status_code == 200

        query_res2 = await query_resource_api(client, sandbox_id, [entries_path])
        assert len(query_res2[entries_path]) == 2
        assert query_res2[entries_path][0]["id"] == "fact_2"