import pytest
from httpx import AsyncClient
from uuid import UUID, uuid4
import datetime

from plugins.core_engine.contracts import Sandbox, Mutation

from plugins.core_engine.tests.conftest import mutate_resource_api, query_resource_api

pytestmark = pytest.mark.e2e

@pytest.fixture
async def setup_sandbox(client: AsyncClient, linear_collection) -> Sandbox:
    """创建一个干净的沙盒用于测试。"""
    create_request_body = {
        "name": "Memoria API via Resource Test",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump(mode='json')},
            "initial_moment": {
                "memoria": {
                    "__global_sequence__": 0,
                    "main_story": {"entries": []}
                }
            }
        }
    }
    response = await client.post("/api/sandboxes", json=create_request_body)
    assert response.status_code == 201
    sandbox = Sandbox.model_validate(response.json())
    yield sandbox
    await client.delete(f"/api/sandboxes/{sandbox.id}")


class TestMemoriaViaResourceAPI:
    """测试通过统一 API **直接、精确地** 管理 Memoria 数据结构。"""

    async def test_memoria_full_crud_in_moment(self, client: AsyncClient, setup_sandbox: Sandbox, mutate_resource_api, query_resource_api):
        """
        验证 API 作为低级工具，能精确地对 Memoria Stream 和 Entry 进行 CRUD 操作。
        """
        sandbox_id = setup_sandbox.id
        stream_path = "moment/memoria/main_story"
        entries_path = f"{stream_path}/entries"
        
        # 1. READ: 验证初始状态
        query_results_init = await query_resource_api(client, sandbox_id, [entries_path])
        assert query_results_init[entries_path] == []

        # 2. CREATE: 
        # [核心修改] 客户端（测试）现在负责构建一个完整的、合法的 MemoryEntry 对象。
        # 这模拟了“专家用户”或前端在知道自己在做什么的情况下的行为。
        new_entry_data = {
            "id": str(uuid4()),
            "sequence_id": 1, # 客户端必须自己管理或知道这个值
            "level": "event",
            "tags": ["exploration"],
            "content": "玩家进入了森林。",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metadata": {}
        }
        
        mutations_create = [
            # 我们同时更新 __global_sequence__，模拟客户端的完整责任
            Mutation(type="UPSERT", path="moment/memoria/__global_sequence__", value=1, mutation_mode="DIRECT"),
            Mutation(type="LIST_APPEND", path=entries_path, value=new_entry_data, mutation_mode="DIRECT")
        ]
        res_create = await mutate_resource_api(client, sandbox_id, mutations_create)
        assert res_create.status_code == 200

        # 3. READ after CREATE: 验证条目被精确地按我们提供的数据创建了
        query_results_after_create = await query_resource_api(client, sandbox_id, [entries_path])
        created_entry = query_results_after_create[entries_path][0]
        
        assert created_entry["content"] == "玩家进入了森林。"
        assert created_entry["sequence_id"] == 1 # <-- 断言现在应该通过了
        assert created_entry["id"] == new_entry_data["id"]

        # 4. UPDATE 和 DELETE 的逻辑保持不变，因为它们本来就是纯数据操作
        entry_content_path = f"{entries_path}/0/content"
        update_mutations = [
            Mutation(type="UPSERT", path=entry_content_path, value="Player found a SHINY key.", mutation_mode="DIRECT")
        ]
        await mutate_resource_api(client, sandbox_id, update_mutations)
        
        delete_mutations = [
            Mutation(type="DELETE", path=f"{entries_path}/0", mutation_mode="DIRECT")
        ]
        await mutate_resource_api(client, sandbox_id, delete_mutations)

        query_after_delete = await query_resource_api(client, sandbox_id, [entries_path])
        assert query_after_delete[entries_path] == []