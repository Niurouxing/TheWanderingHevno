# plugins/core_codex/tests/test_codex_api.py
import pytest
from httpx import AsyncClient
from uuid import UUID

from plugins.core_engine.contracts import Sandbox, GraphCollection
from plugins.core_codex.models import Codex, CodexEntry

# 标记所有测试为异步和E2E
pytestmark = [pytest.mark.asyncio, pytest.mark.e2e]

@pytest.fixture
async def setup_sandbox(client: AsyncClient, sandbox_factory: callable, linear_collection: GraphCollection) -> Sandbox:
    """【E2E Fixture】使用工厂创建一个干净的沙盒用于每个API测试。"""
    sandbox = await sandbox_factory(
        graph_collection=linear_collection,
        initial_lore={"description": "Test Lore"},
        initial_moment={"player_name": "API_Tester"}
    )
    yield sandbox
    # 清理：通过API删除沙盒
    await client.delete(f"/api/sandboxes/{sandbox.id}")


async def get_scope_data(client: AsyncClient, sandbox_id: UUID, scope: str) -> dict:
    """通过API获取指定作用域的数据。"""
    res = await client.get(f"/api/sandboxes/{sandbox_id}/{scope}")
    res.raise_for_status()
    return res.json()


async def test_upsert_codex_in_lore(client: AsyncClient, setup_sandbox: Sandbox):
    """测试：通过 PUT API 在 'lore' 作用域中创建或更新一个 Codex。"""
    sandbox_id = setup_sandbox.id
    original_snapshot_id = setup_sandbox.head_snapshot_id

    codex_name = "world_history"
    new_codex = Codex(entries=[CodexEntry(id="e1", content="c1")])

    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}"
    response = await client.put(url, json=new_codex.model_dump())
    
    assert response.status_code == 200
    assert response.json()["description"] is None

    lore_data = await get_scope_data(client, sandbox_id, "lore")
    assert codex_name in lore_data["codices"]

    # 验证快照ID没有改变
    res_get_after = await client.get(f"/api/sandboxes/{sandbox_id}")
    res_get_after.raise_for_status()
    assert UUID(res_get_after.json()["head_snapshot_id"]) == original_snapshot_id


async def test_add_entry_to_codex_in_moment(client: AsyncClient, setup_sandbox: Sandbox):
    """测试：通过 POST API 在 'moment' 作用域的 Codex 中添加一个 Entry。"""
    sandbox_id = setup_sandbox.id
    original_snapshot_id = setup_sandbox.head_snapshot_id
    
    codex_name = "character_status"
    new_entry = CodexEntry(id="is_poisoned", content="角色中毒", priority=100)

    url = f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}/entries"
    response = await client.post(url, json=new_entry.model_dump())

    assert response.status_code == 201
    
    res_get_after = await client.get(f"/api/sandboxes/{sandbox_id}")
    res_get_after.raise_for_status()
    assert UUID(res_get_after.json()["head_snapshot_id"]) != original_snapshot_id
    
    moment_data = await get_scope_data(client, sandbox_id, "moment")
    assert codex_name in moment_data["codices"]
    assert len(moment_data["codices"][codex_name]["entries"]) == 1


async def test_delete_codex_from_lore(client: AsyncClient, setup_sandbox: Sandbox):
    sandbox_id = setup_sandbox.id
    codex_name = "to_be_deleted"
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=Codex(entries=[]).model_dump())
    
    response = await client.delete(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}")

    assert response.status_code == 204
    
    lore_after = await get_scope_data(client, sandbox_id, "lore")
    assert codex_name not in lore_after.get("codices", {})


async def test_update_full_entry_with_put(client: AsyncClient, setup_sandbox: Sandbox):
    sandbox_id = setup_sandbox.id
    codex_name, entry_id = "rules", "fireball"
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=Codex(entries=[CodexEntry(id=entry_id, content="old")]).model_dump())
    
    updated_entry = CodexEntry(id=entry_id, content="new", priority=20, is_enabled=False)

    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}/entries/{entry_id}"
    response = await client.put(url, json=updated_entry.model_dump())

    assert response.status_code == 200
    entry_after = (await get_scope_data(client, sandbox_id, "lore"))["codices"][codex_name]["entries"][0]
    assert entry_after["content"] == "new"


async def test_patch_entry_in_moment(client: AsyncClient, setup_sandbox: Sandbox):
    sandbox_id = setup_sandbox.id
    codex_name, entry_id = "quest_log", "main_quest"
    await client.put(f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}", json=Codex(entries=[CodexEntry(id=entry_id, content="old")]).model_dump())
    
    url = f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}/entries/{entry_id}"
    response = await client.patch(url, json={"content": "new"})

    assert response.status_code == 200
    entry_after = (await get_scope_data(client, sandbox_id, "moment"))["codices"][codex_name]["entries"][0]
    assert entry_after["content"] == "new"


async def test_delete_entry_from_moment(client: AsyncClient, setup_sandbox: Sandbox):
    sandbox_id = setup_sandbox.id
    codex_name = "inventory"
    entries = [CodexEntry(id="sword", content="s"), CodexEntry(id="shield", content="s")]
    await client.put(f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}", json=Codex(entries=[e.model_dump() for e in entries]).model_dump())
    
    url = f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}/entries/shield"
    response = await client.delete(url, timeout=10)

    assert response.status_code == 204
    entries_after = (await get_scope_data(client, sandbox_id, "moment"))["codices"][codex_name]["entries"]
    assert len(entries_after) == 1
    assert entries_after[0]["id"] == "sword"


async def test_reorder_entries(client: AsyncClient, setup_sandbox: Sandbox):
    sandbox_id = setup_sandbox.id
    codex_name = "spellbook"
    entries = [CodexEntry(id="A", content="a"), CodexEntry(id="B", content="b"), CodexEntry(id="C", content="c")]
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=Codex(entries=[e.model_dump() for e in entries]).model_dump())

    new_order = {"entry_ids": ["C", "A", "B"]}
    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}/entries:reorder"
    response = await client.post(url, json=new_order)
    
    assert response.status_code == 204
    final_ids = [e['id'] for e in (await get_scope_data(client, sandbox_id, "lore"))["codices"][codex_name]["entries"]]
    assert final_ids == ["C", "A", "B"]


async def test_reorder_with_mismatched_ids_fails(client: AsyncClient, setup_sandbox: Sandbox):
    sandbox_id = setup_sandbox.id
    codex_name = "spellbook"
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=Codex(entries=[CodexEntry(id="A", content="a")]).model_dump())
    
    bad_order = {"entry_ids": ["B", "A"]}
    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}/entries:reorder"
    response = await client.post(url, json=bad_order)

    assert response.status_code == 400
    assert "do not match" in response.json()["detail"]