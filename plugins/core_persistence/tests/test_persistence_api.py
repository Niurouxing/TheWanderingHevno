# plugins/core_persistence/tests/test_persistence_api.py

import pytest
from httpx import AsyncClient

from plugins.core_engine.contracts import Sandbox

pytestmark = pytest.mark.e2e

class TestPersistenceAPI:
    """Tests persistence-related API endpoints."""

    async def test_list_assets_sandbox(self, client: AsyncClient, sandbox_factory):
        """
        Tests that the list_assets endpoint for sandboxes correctly reflects
        the creation and deletion of a sandbox.
        """
        # 1. Initially, the list should be empty (or not contain our new sandbox)
        response = await client.get("/api/persistence/assets/sandbox")
        response.raise_for_status()
        initial_sandboxes = response.json()

        # 2. Create a sandbox via the proper engine API
        create_res = await client.post("/api/sandboxes", json={
            "name": "AssetListTest",
            "definition": {"initial_lore": {}, "initial_moment": {}}
        })
        create_res.raise_for_status()
        new_sandbox = Sandbox.model_validate(create_res.json())

        # 3. Check the asset list again
        response_after_create = await client.get("/api/persistence/assets/sandbox")
        response_after_create.raise_for_status()
        sandboxes_after_create = response_after_create.json()
        
        assert len(sandboxes_after_create) == len(initial_sandboxes) + 1
        assert str(new_sandbox.id) in sandboxes_after_create

        # 4. Cleanup
        await client.delete(f"/api/sandboxes/{new_sandbox.id}")