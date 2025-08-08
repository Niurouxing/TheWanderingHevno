# plugins/core_codex/tests/test_codex_api.py
import pytest
from httpx import AsyncClient
from uuid import UUID

from plugins.core_engine.contracts import Sandbox
from plugins.core_codex.models import Codex, CodexEntry

# 标记所有测试为异步
pytestmark = pytest.mark.asyncio

# --- 辅助函数 ---

async def get_scope_data(client: AsyncClient, sandbox_id: UUID, scope: str) -> dict:
    """通过API获取指定作用域的数据。"""
    res = await client.get(f"/api/sandboxes/{sandbox_id}/{scope}")
    res.raise_for_status()
    return res.json()

# --- 现有测试 (保持不变) ---

async def test_upsert_codex_in_lore(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """
    测试：通过 PUT API 在 'lore' 作用域中创建或更新一个 Codex。
    """
    # Arrange
    sandbox_id = sandbox_in_db.id
    history_before_res = await client.get(f"/api/sandboxes/{sandbox_id}/history")
    history_count_before = len(history_before_res.json())

    codex_name = "world_history"
    new_codex = Codex(
        description="世界的宏大历史",
        entries=[
            CodexEntry(id="creation", content="世界由巨龙创造。"),
            CodexEntry(id="first_age", content="第一纪元是精灵的时代。")
        ]
    )

    # Act
    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}"
    response = await client.put(url, json=new_codex.model_dump())
    
    # Assert
    assert response.status_code == 200
    updated_sandbox_data = response.json()
    assert codex_name in updated_sandbox_data["lore"]["codices"]
    assert updated_sandbox_data["lore"]["codices"][codex_name]["description"] == "世界的宏大历史"

    lore_data = await get_scope_data(client, sandbox_id, "lore")
    assert codex_name in lore_data["codices"]
    assert len(lore_data["codices"][codex_name]["entries"]) == 2

    history_after_res = await client.get(f"/api/sandboxes/{sandbox_id}/history")
    history_count_after = len(history_after_res.json())
    assert history_count_after == history_count_before, "Updating lore should not create new snapshots"

async def test_add_entry_to_codex_in_moment(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """
    测试：通过 POST API 在 'moment' 作用域的 Codex 中添加一个 Entry。
    """
    # Arrange
    sandbox_id = sandbox_in_db.id
    history_before_res = await client.get(f"/api/sandboxes/{sandbox_id}/history")
    history_count_before = len(history_before_res.json())
    
    codex_name = "character_status"
    new_entry = CodexEntry(id="is_poisoned", content="角色当前处于中毒状态。", priority=100)

    # Act
    url = f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}/entries"
    response = await client.post(url, json=new_entry.model_dump())

    # Assert
    assert response.status_code == 200
    
    history_after_res = await client.get(f"/api/sandboxes/{sandbox_id}/history")
    history_count_after = len(history_after_res.json())
    assert history_count_after == history_count_before + 1, "Updating moment must create a new snapshot"
    
    moment_data = await get_scope_data(client, sandbox_id, "moment")
    assert codex_name in moment_data["codices"]
    entries = moment_data["codices"][codex_name]["entries"]
    assert len(entries) == 1
    assert entries[0]["id"] == "is_poisoned"

# ===================================================
# === 新增测试用例 ===
# ===================================================

# --- DELETE Codex ---

async def test_delete_codex_from_lore(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """测试：从 lore 中删除一个已存在的 Codex。"""
    # Arrange
    sandbox_id = sandbox_in_db.id
    codex_name = "to_be_deleted"
    codex_def = Codex(entries=[CodexEntry(id="e1", content="c1")])
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=codex_def.model_dump())
    
    lore_before = await get_scope_data(client, sandbox_id, "lore")
    assert codex_name in lore_before["codices"]
    
    history_count_before = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())

    # Act
    response = await client.delete(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}")

    # Assert
    assert response.status_code == 200
    
    lore_after = await get_scope_data(client, sandbox_id, "lore")
    assert codex_name not in lore_after["codices"]

    history_count_after = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())
    assert history_count_after == history_count_before, "Deleting from lore should not create a snapshot"

# --- UPDATE Entry (PUT & PATCH) ---

async def test_update_full_entry_with_put(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """测试：使用 PUT 完整更新一个 lore 中的条目。"""
    # Arrange
    sandbox_id = sandbox_in_db.id
    codex_name = "rules"
    entry_id = "fireball"
    original_entry = CodexEntry(id=entry_id, content="Fireball does 10 damage.", priority=10)
    codex_def = Codex(entries=[original_entry.model_dump()])
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=codex_def.model_dump())
    
    updated_entry_data = CodexEntry(id=entry_id, content="Fireball now does 15 damage!", priority=20, is_enabled=False)

    # Act
    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}/entries/{entry_id}"
    response = await client.put(url, json=updated_entry_data.model_dump())

    # Assert
    assert response.status_code == 200
    lore_data = await get_scope_data(client, sandbox_id, "lore")
    entry_after_update = lore_data["codices"][codex_name]["entries"][0]

    assert entry_after_update["content"] == "Fireball now does 15 damage!"
    assert entry_after_update["priority"] == 20
    assert entry_after_update["is_enabled"] is False

async def test_patch_entry_in_moment(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """测试：使用 PATCH 局部更新 moment 中的条目，并验证快照创建。"""
    # Arrange
    sandbox_id = sandbox_in_db.id
    codex_name = "quest_log"
    entry_id = "main_quest"
    original_entry = CodexEntry(id=entry_id, content="Defeat the dragon.", is_enabled=True)
    codex_def = Codex(entries=[original_entry.model_dump()])
    # 先在 moment 中创建初始状态
    await client.put(f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}", json=codex_def.model_dump())
    
    history_count_before = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())
    
    patch_data = {"content": "Befriend the dragon."}

    # Act
    url = f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}/entries/{entry_id}"
    response = await client.patch(url, json=patch_data)

    # Assert
    assert response.status_code == 200
    history_count_after = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())
    assert history_count_after == history_count_before + 1, "Patching moment must create a new snapshot"
    
    moment_data = await get_scope_data(client, sandbox_id, "moment")
    entry_after_update = moment_data["codices"][codex_name]["entries"][0]
    
    assert entry_after_update["content"] == "Befriend the dragon."
    assert entry_after_update["is_enabled"] is True, "Unchanged fields should remain the same"

# --- DELETE Entry ---

async def test_delete_entry_from_moment(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """测试：从 moment 中的一个多条目 Codex 中删除一个条目。"""
    # Arrange
    sandbox_id = sandbox_in_db.id
    codex_name = "inventory"
    entries = [
        CodexEntry(id="sword", content="A sharp blade."),
        CodexEntry(id="shield", content="A sturdy shield."),
        CodexEntry(id="potion", content="A healing potion."),
    ]
    codex_def = Codex(entries=[e.model_dump() for e in entries])
    # 在 moment 中创建初始状态
    await client.put(f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}", json=codex_def.model_dump())
    
    history_count_before = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())

    # Act: 删除中间的 'shield'
    url = f"/api/sandboxes/{sandbox_id}/moment/codices/{codex_name}/entries/shield"
    response = await client.delete(url)

    # Assert
    assert response.status_code == 200
    history_count_after = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())
    assert history_count_after == history_count_before + 1, "Deleting from moment must create a new snapshot"
    
    moment_data = await get_scope_data(client, sandbox_id, "moment")
    entries_after = moment_data["codices"][codex_name]["entries"]
    entry_ids_after = [e['id'] for e in entries_after]
    
    assert len(entries_after) == 2
    assert entry_ids_after == ["sword", "potion"]
    
# --- REORDER Entries ---

async def test_reorder_entries(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """测试：使用 API 对 lore 中的条目进行重排序。"""
    # Arrange
    sandbox_id = sandbox_in_db.id
    codex_name = "spellbook"
    entries = [
        CodexEntry(id="A", content="Spell A"),
        CodexEntry(id="B", content="Spell B"),
        CodexEntry(id="C", content="Spell C"),
    ]
    codex_def = Codex(entries=[e.model_dump() for e in entries])
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=codex_def.model_dump())

    history_count_before = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())

    # Act
    new_order = {"entry_ids": ["C", "A", "B"]}
    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}/entries:reorder"
    response = await client.post(url, json=new_order)
    
    # Assert
    assert response.status_code == 200 # 现在应该能成功了
    
    lore_data = await get_scope_data(client, sandbox_id, "lore")
    final_entry_ids = [e['id'] for e in lore_data["codices"][codex_name]["entries"]]
    assert final_entry_ids == ["C", "A", "B"]

    history_count_after = len((await client.get(f"/api/sandboxes/{sandbox_id}/history")).json())
    assert history_count_after == history_count_before, "Reordering in lore should not create a snapshot"

async def test_reorder_with_mismatched_ids_fails(
    client: AsyncClient, 
    sandbox_in_db: Sandbox
):
    """测试：如果重排序请求提供的ID列表与现有ID不匹配，应返回400错误。"""
    # Arrange
    sandbox_id = sandbox_in_db.id
    codex_name = "spellbook"
    entries = [CodexEntry(id="A", content="Spell A"), CodexEntry(id="B", content="Spell B")]
    codex_def = Codex(entries=[e.model_dump() for e in entries])
    await client.put(f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}", json=codex_def.model_dump())

    # Act: 尝试用不匹配的 ID 列表进行重排
    bad_order = {"entry_ids": ["B", "A", "X"]} # 'X' is extra
    url = f"/api/sandboxes/{sandbox_id}/lore/codices/{codex_name}/entries:reorder"
    response = await client.post(url, json=bad_order)

    # Assert
    assert response.status_code == 400 # 现在应该返回我们自己逻辑中定义的400错误
    assert "do not match" in response.json()["detail"]