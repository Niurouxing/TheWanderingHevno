# plugins/core_persistence/stores.py
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID

# 从 core_engine 导入接口定义
from plugins.core_engine.contracts import Sandbox, StateSnapshot, SnapshotStoreInterface, SandboxStoreInterface
from backend.core.serialization import pickle_fallback_encoder
from .contracts import PersistenceServiceInterface
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# 继承自 SandboxStoreInterface
class PersistentSandboxStore(SandboxStoreInterface):
    def __init__(self, persistence_service: PersistenceServiceInterface):
        self._persistence = persistence_service
        self._cache: Dict[UUID, Sandbox] = {}
        self._locks: Dict[UUID, asyncio.Lock] = {}
        # 为 SnapshotStore 添加一个依赖，以便在删除时可以调用它
        self._snapshot_store: Optional[SnapshotStoreInterface] = None
        self._container: Optional['Container'] = None # type: ignore
        logger.info("PersistentSandboxStore initialized (cache is empty).")

    # 提供一种方式来注入容器，以便稍后解析 snapshot_store
    def set_container(self, container: 'Container'): # type: ignore
        self._container = container

    def _get_lock(self, sandbox_id: UUID) -> asyncio.Lock:
        if sandbox_id not in self._locks:
            self._locks.setdefault(sandbox_id, asyncio.Lock())
        return self._locks[sandbox_id]
        
    async def initialize(self):
        logger.info("Pre-loading all sandboxes and their snapshots from disk into cache...")
        count = 0
        
        # 1. 在初始化开始时，确保我们能访问到 snapshot_store
        if not self._container:
             logger.error("Container not set on PersistentSandboxStore. Cannot pre-load snapshots.")
             return
        
        # 解析一次并缓存，避免在循环中重复解析
        snapshot_store: SnapshotStoreInterface = self._container.resolve("snapshot_store")
        
        sandbox_ids = await self._persistence.list_sandbox_ids()
        for sid_str in sandbox_ids:
            try:
                sid = UUID(sid_str)
                data = await self._persistence.load_sandbox(sid)
                if data:
                    sandbox = Sandbox.model_validate(data)
                    self._cache[sid] = sandbox
                    count += 1
                    
                    # 2. 对于每一个加载的沙盒，立即让 snapshot_store 去加载它所有的快照
                    #    find_by_sandbox 会自动将加载的快照放入 snapshot_store 的缓存中
                    logger.debug(f"Pre-loading snapshots for sandbox {sid}...")
                    await snapshot_store.find_by_sandbox(sid)

            except (ValueError, FileNotFoundError, ValidationError) as e:
                logger.warning(f"Skipping invalid sandbox directory '{sid_str}': {e}")
        logger.info(f"Successfully pre-loaded {count} sandboxes and their associated snapshots into cache.")

    async def save(self, sandbox: Sandbox):
        lock = self._get_lock(sandbox.id)
        async with lock:
            # 使用 mode='json' 并提供 fallback 函数
            data = sandbox.model_dump(mode='json', fallback=pickle_fallback_encoder)

            await self._persistence.save_sandbox(sandbox.id, data)
            self._cache[sandbox.id] = sandbox
            
    def get(self, key: UUID) -> Optional[Sandbox]:
        return self._cache.get(key)

    async def delete(self, key: UUID):
        lock = self._get_lock(key)
        async with lock:
            # 正确地从容器中解析 snapshot_store 并调用其方法
            if self._container:
                if not self._snapshot_store:
                    self._snapshot_store = self._container.resolve("snapshot_store")
                await self._snapshot_store.delete_all_for_sandbox(key)
            else:
                 logger.warning("Container not set on PersistentSandboxStore, cannot delete snapshots automatically.")

            await self._persistence.delete_sandbox(key)
            self._cache.pop(key, None)
            self._locks.pop(key, None)

    def values(self) -> List[Sandbox]:
        return list(self._cache.values())
        
    def __contains__(self, key: UUID) -> bool:
        return key in self._cache
    
    def clear(self) -> None:
        logger.warning("`clear` called on PersistentSandboxStore, but it does nothing to disk state. Cache is NOT cleared.")
        pass


class PersistentSnapshotStore(SnapshotStoreInterface):
    """
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
            # 同样，使用 mode='json' 并提供 fallback 函数
            data = snapshot.model_dump(mode='json', fallback=pickle_fallback_encoder)
          
            await self._persistence.save_snapshot(snapshot.sandbox_id, snapshot.id, data)
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
        snapshots_data = await self._persistence.load_all_snapshots_for_sandbox(sandbox_id)
        for data in snapshots_data:
            try:
                s = StateSnapshot.model_validate(data)
                self._cache[s.id] = s
            except ValidationError as e:
                logger.warning(f"Skipping snapshot with invalid data for sandbox {sandbox_id}: {e}")
        
        # 即使磁盘上没有，也要确保返回缓存中可能存在的（例如，刚创建还未写入的）
        relevant_snapshots = [s for s in self._cache.values() if s.sandbox_id == sandbox_id]
        # 去重，以防万一
        unique_snapshots = {s.id: s for s in relevant_snapshots}.values()
        return sorted(list(unique_snapshots), key=lambda s: s.created_at)

    async def delete_all_for_sandbox(self, sandbox_id: UUID) -> None:
        """实现接口中新加的方法"""
        await self._persistence.delete_all_for_sandbox(sandbox_id)
        # 从缓存中也移除
        ids_to_remove = [sid for sid, s in self._cache.items() if s.sandbox_id == sandbox_id]
        for sid in ids_to_remove:
            self._cache.pop(sid, None)
            self._locks.pop(sid, None)

    async def delete(self, snapshot_id: UUID) -> None:
        """异步删除指定的快照，包括其持久化文件和缓存条目。"""
        snapshot = self.get(snapshot_id)
        if not snapshot:
            # 如果快照不存在，静默返回，因为目标已经达成
            return
            
        lock = self._get_lock(snapshot_id)
        async with lock:
            await self._persistence.delete_snapshot(snapshot.sandbox_id, snapshot.id)
            # 从缓存和锁字典中移除
            self._cache.pop(snapshot_id, None)
            self._locks.pop(snapshot_id, None)
            logger.info(f"Deleted snapshot {snapshot_id} from persistence and cache.")


    def clear(self) -> None:
        """此操作在持久化存储中无意义，记录警告并忽略。"""
        logger.warning("`clear` called on PersistentSnapshotStore, but it does nothing to disk state. Cache is NOT cleared.")
        pass