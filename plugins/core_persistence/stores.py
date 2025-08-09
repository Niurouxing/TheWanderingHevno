# plugins/core_persistence/stores.py
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID

from plugins.core_engine.contracts import Sandbox, StateSnapshot, SnapshotStoreInterface
from .contracts import PersistenceServiceInterface

logger = logging.getLogger(__name__)

class PersistentSandboxStore:
    """
    管理沙盒的持久化和缓存。
    - 使用异步初始化模式在启动时预加载缓存。
    - 所有对持久化层的调用现在都是非阻塞的。
    """
    def __init__(self, persistence_service: PersistenceServiceInterface):
        self._persistence = persistence_service
        self._cache: Dict[UUID, Sandbox] = {}
        # 为每个沙盒ID创建一个独立的锁，以实现更细粒度的并发控制
        self._locks: Dict[UUID, asyncio.Lock] = {}
        logger.info("PersistentSandboxStore initialized (cache is empty).")

    def _get_lock(self, sandbox_id: UUID) -> asyncio.Lock:
        # 在多线程/协程环境中安全地获取或创建锁
        if sandbox_id not in self._locks:
            self._locks.setdefault(sandbox_id, asyncio.Lock())
        return self._locks[sandbox_id]
        
    async def initialize(self):
        """
        异步初始化方法，在应用启动时被调用。
        从磁盘预加载所有沙盒到内存缓存中。
        """
        logger.info("Pre-loading all sandboxes from disk into cache...")
        count = 0
        # 使用 await 调用异步的 list_sandbox_ids
        sandbox_ids = await self._persistence.list_sandbox_ids()
        for sid_str in sandbox_ids:
            try:
                sid = UUID(sid_str)
                # 使用 await 调用异步的 load_sandbox
                sandbox = await self._persistence.load_sandbox(sid)
                if sandbox:
                    self._cache[sid] = sandbox
                    count += 1
            except (ValueError, FileNotFoundError) as e:
                logger.warning(f"Skipping invalid sandbox directory '{sid_str}': {e}")
        logger.info(f"Successfully pre-loaded {count} sandboxes into cache.")

    async def save(self, sandbox: Sandbox):
        """异步保存沙盒到磁盘并更新缓存。"""
        lock = self._get_lock(sandbox.id)
        async with lock:
            # 使用 await 调用异步的 save_sandbox
            await self._persistence.save_sandbox(sandbox)
            self._cache[sandbox.id] = sandbox
            
    def get(self, key: UUID) -> Optional[Sandbox]:
        """
        从缓存中同步获取沙盒。
        这依赖于 `initialize` 预加载或 `save` 方法来填充缓存。
        对于一个总是先list/create再get的UI流，这是安全的。
        """
        return self._cache.get(key)

    async def delete(self, key: UUID):
        """异步从磁盘和缓存中删除沙盒。"""
        lock = self._get_lock(key)
        async with lock:
            # 使用 await 调用异步的 delete_sandbox
            await self._persistence.delete_sandbox(key)
            self._cache.pop(key, None)
            self._locks.pop(key, None)

    def values(self) -> List[Sandbox]:
        """从缓存中同步获取所有沙盒的值。"""
        return list(self._cache.values())
        
    def __contains__(self, key: UUID) -> bool:
        """同步检查沙盒是否存在于缓存中。"""
        return key in self._cache
    
    def clear(self) -> None:
        """此操作在持久化存储中无意义，记录警告并忽略。"""
        logger.warning("`clear` called on PersistentSandboxStore, but it does nothing to disk state. Cache is NOT cleared.")
        pass


class PersistentSnapshotStore(SnapshotStoreInterface):
    """
    【已重构为异步】
    管理快照的持久化和缓存。
    - 快照按需从磁盘加载。
    - 所有对持久化层的调用现在都是非阻塞的。
    """
    def __init__(self, persistence_service: PersistenceServiceInterface):
        self._persistence = persistence_service
        self._cache: Dict[UUID, StateSnapshot] = {}
        # 为每个快照ID创建一个独立的锁，以实现原子性保存
        self._locks: Dict[UUID, asyncio.Lock] = {}
        logger.info("PersistentSnapshotStore initialized.")

    def _get_lock(self, snapshot_id: UUID) -> asyncio.Lock:
        return self._locks.setdefault(snapshot_id, asyncio.Lock())

    async def save(self, snapshot: StateSnapshot) -> None:
        """异步保存快照到磁盘并更新缓存。"""
        lock = self._get_lock(snapshot.id)
        async with lock:
            # 使用 await 调用异步的 save_snapshot
            await self._persistence.save_snapshot(snapshot)
            self._cache[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        """
        从缓存中同步获取快照。
        注意：此方法不会从磁盘加载。它依赖于 find_by_sandbox 或 save 来填充缓存。
        这是一个设计权衡，以避免在get()中需要sandbox_id。
        """
        return self._cache.get(snapshot_id)

    async def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        """异步加载属于特定沙盒的所有快照，并更新缓存。"""
        # 使用 await 调用异步的 load_all_snapshots_for_sandbox
        disk_snapshots = await self._persistence.load_all_snapshots_for_sandbox(sandbox_id)
        for s in disk_snapshots:
            # 用从磁盘加载的最新数据更新缓存
            self._cache[s.id] = s
        
        # 即使磁盘上没有，也要确保返回缓存中可能存在的（例如，刚创建还未写入的）
        relevant_snapshots = [s for s in self._cache.values() if s.sandbox_id == sandbox_id]
        # 去重，以防万一
        unique_snapshots = {s.id: s for s in relevant_snapshots}.values()
        return sorted(list(unique_snapshots), key=lambda s: s.created_at)

    def clear(self) -> None:
        """此操作在持久化存储中无意义，记录警告并忽略。"""
        logger.warning("`clear` called on PersistentSnapshotStore, but it does nothing to disk state. Cache is NOT cleared.")
        pass