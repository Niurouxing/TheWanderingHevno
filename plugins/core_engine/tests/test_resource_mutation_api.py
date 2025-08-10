import pytest
from httpx import AsyncClient
from typing import List
from uuid import UUID

from plugins.core_engine.contracts import (
    Sandbox,
    GraphCollection,
    MutateResourceRequest, # 导入新的API模型
    Mutation
)

# 标记此文件中的所有测试都是端到端(e2e)测试
pytestmark = pytest.mark.e2e



async def query_resource(client: AsyncClient, sandbox_id: UUID, paths: List[str]) -> dict:
    """辅助函数，用于发送query请求并返回结果字典。"""
    request_body = {"paths": paths}
    response = await client.post(
        f"/api/sandboxes/{sandbox_id}/resource:query",
        json=request_body
    )
    assert response.status_code == 200, f"Query failed: {response.text}"
    return response.json()["results"]


@pytest.fixture
async def setup_sandbox(client: AsyncClient, linear_collection: GraphCollection) -> Sandbox:
    """
    【E2E Fixture】通过API创建沙盒，为每个测试提供干净、隔离的环境。
    这个fixture保持不变，因为它非常有用。
    """
    create_request_body = {
        "name": "Mutation API Test Sandbox",
        "definition": {
            "initial_lore": {"graphs": linear_collection.model_dump(mode='json')},
            "initial_moment": {"player_name": "Mutator"}
        }
    }
    response = await client.post("/api/sandboxes", json=create_request_body)
    assert response.status_code == 201
    
    sandbox = Sandbox.model_validate(response.json())
    yield sandbox
    # 清理
    await client.delete(f"/api/sandboxes/{sandbox.id}")

async def mutate_resource(client: AsyncClient, sandbox_id: UUID, mutations: List[Mutation]):
    """辅助函数，用于发送mutate请求并处理基本断言。"""
    request_body = MutateResourceRequest(mutations=mutations).model_dump(mode='json')
    response = await client.post(
        f"/api/sandboxes/{sandbox_id}/resource:mutate",
        json=request_body
    )
    return response


class TestResourceMutationAPI:
    """【E2E】测试统一的 /resource:mutate 端点。"""

    async def test_upsert_and_delete_in_lore(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试对 lore 作用域的 UPSERT 和 DELETE 操作。"""
        sandbox_id = setup_sandbox.id

        # 1. UPSERT: 添加一个新的codex
        codex_data = {"description": "A new codex."}
        res_upsert = await mutate_resource(client, sandbox_id, [
            Mutation(type="UPSERT", path="lore/codices/new_codex", value=codex_data)
        ])
        assert res_upsert.status_code == 200

        # 验证修改
        res_get = await client.get(f"/api/sandboxes/{sandbox_id}")
        assert res_get.json()["lore"]["codices"]["new_codex"] == codex_data
        original_snapshot_id = res_get.json()["head_snapshot_id"]

        # 2. DELETE: 删除刚刚添加的codex
        res_delete = await mutate_resource(client, sandbox_id, [
            Mutation(type="DELETE", path="lore/codices/new_codex")
        ])
        assert res_delete.status_code == 200
        
        # 验证删除，并确认快照ID未变
        res_get_after = await client.get(f"/api/sandboxes/{sandbox_id}")
        assert "new_codex" not in res_get_after.json()["lore"]["codices"]
        assert res_get_after.json()["head_snapshot_id"] == original_snapshot_id, \
            "Modifying lore should NOT change the head snapshot ID"

    async def test_list_append_in_definition(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试对 definition/initial_lore 作用域的 LIST_APPEND 操作。"""
        sandbox_id = setup_sandbox.id
        
        # 向 initial_lore/graphs/main/nodes 列表追加一个新节点
        new_node_data = {"id": "D_appended", "run": []}
        res_append = await mutate_resource(client, sandbox_id, [
            Mutation(type="LIST_APPEND", path="definition/initial_lore/graphs/main/nodes", value=new_node_data)
        ])
        assert res_append.status_code == 200

        # 验证
        res_get = await client.get(f"/api/sandboxes/{sandbox_id}")
        nodes = res_get.json()["definition"]["initial_lore"]["graphs"]["main"]["nodes"]
        assert len(nodes) == 4 # 原有3个 + 新增1个
        assert nodes[3]["id"] == "D_appended"

    async def test_moment_mutation_direct_mode(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试对 moment 的 DIRECT (可变) 修改模式。"""
        sandbox_id = setup_sandbox.id
        
        original_snapshot_id = str(setup_sandbox.head_snapshot_id)

        # 使用 DIRECT 模式修改 moment
        mutations = [
            Mutation(type="UPSERT", path="moment/player_name", value="DirectMutator"),
            Mutation(type="UPSERT", path="moment/new_field", value=True)
        ]
        res_mutate = await mutate_resource(client, sandbox_id, mutations)
        assert res_mutate.status_code == 200
    
        # 验证返回的快照ID【未变】
        assert res_mutate.json()["head_snapshot_id"] == original_snapshot_id

        # 使用新的 query API 来验证快照内容确实被修改了
        query_results = await query_resource(
            client, 
            sandbox_id, 
            ["moment/player_name", "moment/new_field"]
        )
        
        assert query_results["moment/player_name"] == "DirectMutator"
        assert query_results["moment/new_field"] is True


    async def test_moment_mutation_snapshot_mode(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试对 moment 的 SNAPSHOT (不可变) 修改模式。"""
        sandbox_id = setup_sandbox.id

        original_snapshot_id = str(setup_sandbox.head_snapshot_id)
    
        # 使用 SNAPSHOT 模式修改 moment
        mutations = [
            Mutation(
                type="UPSERT", 
                path="moment/player_name", 
                value="SnapshotMutator",
                mutation_mode="SNAPSHOT" # 明确指定模式
            )
        ]
        res_mutate = await mutate_resource(client, sandbox_id, mutations)
        assert res_mutate.status_code == 200
    
        # 验证返回了【新】的快照ID
        new_snapshot_id = res_mutate.json()["head_snapshot_id"]
        assert new_snapshot_id != original_snapshot_id

        # 使用新的 query API 来验证新快照的内容是正确的
        query_results = await query_resource(client, sandbox_id, ["moment/player_name"])
        assert query_results["moment/player_name"] == "SnapshotMutator"

        # 验证历史记录依然正确
        res_history = await client.get(f"/api/sandboxes/{sandbox_id}/history")
        history_data = res_history.json()
        assert len(history_data) == 2
        assert history_data[1]["id"] == new_snapshot_id
        assert history_data[1]["parent_snapshot_id"] == original_snapshot_id

    
    async def test_atomic_batch_mutation(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试一个请求中包含多个修改操作的原子性。"""
        sandbox_id = setup_sandbox.id

        # 1. 准备：先为 moment 添加一个空的 log 列表，以便后续 LIST_APPEND
        # 注意：这一步本身也是一次直接修改
        init_mutations = [Mutation(type="UPSERT", path="moment/log", value=[], mutation_mode="DIRECT")]
        res_init = await mutate_resource(client, sandbox_id, init_mutations)
        assert res_init.status_code == 200

        # 2. Arrange: 定义一个跨越多个作用域的批量修改操作
        batch_mutations = [
            Mutation(type="UPSERT", path="lore/setting", value="fantasy"),
            Mutation(type="DELETE", path="definition/initial_lore/graphs/main/nodes/1"), # 删除节点B
            Mutation(type="LIST_APPEND", path="moment/log", value="Batch operation performed", mutation_mode="DIRECT")
        ]

        # 3. Act: 执行批量操作
        res_mutate = await mutate_resource(client, sandbox_id, batch_mutations)
        assert res_mutate.status_code == 200

        # 4. Assert: 使用一次 query 请求验证所有修改都已生效
        query_paths = [
            "lore/setting",
            "definition/initial_lore/graphs/main/nodes",
            "moment/log"
        ]
        query_results = await query_resource(client, sandbox_id, query_paths)

        assert query_results["lore/setting"] == "fantasy"
        nodes = query_results["definition/initial_lore/graphs/main/nodes"]
        assert len(nodes) == 2
        assert nodes[1]["id"] == "C" # 节点B已被删除
        assert query_results["moment/log"] == ["Batch operation performed"]



class TestMutationApiErrorHandling:
    """【E2E】测试统一API的错误处理。"""

    async def test_invalid_path_root(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试对不允许的根路径（如 'id'）的修改。"""
        mutations = [Mutation(type="UPSERT", path="id/some_value", value="hacked")]
        response = await mutate_resource(client, setup_sandbox.id, mutations)
        assert response.status_code == 422 # Unprocessable Entity
        assert "Invalid mutation path root" in response.json()["detail"]

    async def test_mixed_moment_mutation_modes(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试在同一次请求中混合使用 DIRECT 和 SNAPSHOT 模式。"""
        mutations = [
            Mutation(type="UPSERT", path="moment/a", value=1, mutation_mode="DIRECT"),
            Mutation(type="UPSERT", path="moment/b", value=2, mutation_mode="SNAPSHOT"),
        ]
        response = await mutate_resource(client, setup_sandbox.id, mutations)
        assert response.status_code == 422
        assert "must use the same 'mutation_mode'" in response.json()["detail"]

    async def test_mutation_failure_rolls_back_changes(self, client: AsyncClient, setup_sandbox: Sandbox):
        """测试如果一个操作失败，整个批次的操作都不会被应用。"""
        sandbox_id = setup_sandbox.id
        
        res_get_before = await client.get(f"/api/sandboxes/{sandbox_id}")
        original_lore = res_get_before.json()["lore"]

        # 批次中包含一个无效操作（向一个非列表对象追加）
        invalid_mutations = [
            Mutation(type="UPSERT", path="lore/valid_change", value=True),
            Mutation(type="LIST_APPEND", path="lore/valid_change", value="invalid")
        ]

        response = await mutate_resource(client, sandbox_id, invalid_mutations)
        assert response.status_code == 422 # 应该是 422 因为是类型错误
        assert "Cannot use LIST_APPEND on a non-list" in response.json()["detail"]

        # 验证沙盒状态未被改变
        res_get_after = await client.get(f"/api/sandboxes/{sandbox_id}")
        final_lore = res_get_after.json()["lore"]
        assert final_lore == original_lore, "Lore should not have changed after a failed mutation"