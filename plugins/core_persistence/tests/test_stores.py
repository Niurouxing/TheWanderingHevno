# plugins/core_persistence/tests/test_stores.py

import pytest
import uuid
from pathlib import Path
from typing import Tuple

from backend.core.contracts import Container
from plugins.core_engine.contracts import Sandbox, StateSnapshot, SnapshotStoreInterface
from plugins.core_persistence.contracts import PersistenceServiceInterface
from plugins.core_persistence.stores import PersistentSandboxStore

pytestmark = pytest.mark.asyncio


@pytest.fixture
def test_sandbox() -> Sandbox:
    """Provides a simple Sandbox instance for testing."""
    return Sandbox(
        name="Persistence Test Sandbox",
        definition={"initial_lore": {}, "initial_moment": {}}
    )

@pytest.fixture
def test_snapshot(test_sandbox: Sandbox) -> StateSnapshot:
    """Provides a simple StateSnapshot instance linked to the test_sandbox."""
    return StateSnapshot(sandbox_id=test_sandbox.id, moment={"turn": 1})


class TestPersistentStores:
    """
    Integration tests for PersistentSandboxStore and PersistentSnapshotStore.
    These tests verify the interaction between the caching stores and the
    underlying file-based persistence service.
    """

    async def test_sandbox_store_lifecycle(
        self,
        test_engine_setup: Tuple[None, Container, None],
        test_sandbox: Sandbox
    ):
        """
        Tests the full lifecycle of a Sandbox: save, get from cache,
        reload from disk after cache clear, and delete.
        """
        _, container, _ = test_engine_setup
        sandbox_store: PersistentSandboxStore = container.resolve("sandbox_store")
        persistence_service: PersistenceServiceInterface = container.resolve("persistence_service")
        sandbox_dir = persistence_service.sandboxes_root_dir / str(test_sandbox.id)

        # 1. Save
        await sandbox_store.save(test_sandbox)
        assert (sandbox_dir / "sandbox.json").is_file()

        # 2. Get from cache
        cached_sandbox = sandbox_store.get(test_sandbox.id)
        assert cached_sandbox is not None
        assert cached_sandbox.id == test_sandbox.id

        # 3. Simulate app restart: clear cache and re-initialize
        sandbox_store._cache.clear()
        assert sandbox_store.get(test_sandbox.id) is None  # Cache is now empty
        await sandbox_store.initialize()

        # 4. Get again, should be loaded from disk
        reloaded_sandbox = sandbox_store.get(test_sandbox.id)
        assert reloaded_sandbox is not None
        assert reloaded_sandbox.name == "Persistence Test Sandbox"

        # 5. Delete
        await sandbox_store.delete(test_sandbox.id)
        assert not sandbox_dir.exists()
        assert sandbox_store.get(test_sandbox.id) is None

    async def test_snapshot_store_lifecycle(
        self,
        test_engine_setup: Tuple[None, Container, None],
        test_sandbox: Sandbox,
        test_snapshot: StateSnapshot
    ):
        """
        Tests the full lifecycle of a Snapshot: save, get from cache,
        find and load from disk, and verify deletion via sandbox deletion.
        """
        _, container, _ = test_engine_setup
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        persistence_service: PersistenceServiceInterface = container.resolve("persistence_service")
        snapshot_file = persistence_service.sandboxes_root_dir / str(test_sandbox.id) / "snapshots" / f"{test_snapshot.id}.json"

        # 1. Save
        await snapshot_store.save(test_snapshot)
        assert snapshot_file.is_file()

        # 2. Get from cache
        cached_snapshot = snapshot_store.get(test_snapshot.id)
        assert cached_snapshot is not None
        assert cached_snapshot.moment == {"turn": 1}

        # 3. Clear cache and find by sandbox (should reload from disk)
        snapshot_store._cache.clear() # type: ignore
        assert snapshot_store.get(test_snapshot.id) is None
        
        found_snapshots = await snapshot_store.find_by_sandbox(test_sandbox.id)
        assert len(found_snapshots) == 1
        assert found_snapshots[0].id == test_snapshot.id

        # 4. Verify it's back in the cache
        reloaded_snapshot = snapshot_store.get(test_snapshot.id)
        assert reloaded_snapshot is not None
        
        # 5. Deletion is handled by deleting the parent sandbox
        await persistence_service.delete_sandbox(test_sandbox.id)
        assert not snapshot_file.exists()