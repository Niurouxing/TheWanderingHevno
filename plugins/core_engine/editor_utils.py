# plugins/core_engine/editor_utils.py
import logging
from copy import deepcopy
from uuid import UUID
from typing import Callable, Dict, Any

from .contracts import Sandbox, EditorUtilsServiceInterface, SnapshotStoreInterface, StateSnapshot
from .contracts import SandboxStoreInterface, SnapshotStoreInterface

logger = logging.getLogger(__name__)

class EditorUtilsService(EditorUtilsServiceInterface):
    """
    实现了用于安全执行“创作式”修改的核心工具的接口。
    这个服务现在完全是异步的，以匹配底层持久化层的 I/O 操作。
    """

    def __init__(self, sandbox_store: SandboxStoreInterface, snapshot_store: SnapshotStoreInterface):
        """
        通过依赖注入获取持久化存储的实例。
        """
        self._sandbox_store = sandbox_store
        self._snapshot_store = snapshot_store
    
    
    async def perform_sandbox_update(self, sandbox: Sandbox, update_function: Callable[[Sandbox], None]) -> Sandbox:
        """
        直接在 Sandbox 对象上执行一个修改函数。
        此函数用于对 'definition' 和 'lore' 作用域进行“创作式”修改。
        它不创建新的快照，但会异步地将沙盒的更改持久化。
        """
        # 1. 在内存中的 Sandbox 对象上应用修改
        update_function(sandbox)
        
        # 2. 添加 await，确保沙盒的更改被异步写入文件系统
        await self._sandbox_store.save(sandbox)
        
        logger.debug(f"Updated and persisted sandbox '{sandbox.id}' for lore/definition change.")
        return sandbox

    async def perform_live_moment_update(
        self,
        sandbox: Sandbox,
        # 移除了多余的 snapshot_store 参数，以匹配接口契约。
        # 服务实例应通过 self._snapshot_store 访问。
        update_function: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Sandbox:
        """
        安全地修改当前沙盒的 'moment' 状态，这必须创建一个新的历史快照。
        所有对文件系统的操作现在都是异步的。
        """
        if not sandbox.head_snapshot_id:
            raise ValueError("Cannot update moment: Sandbox has no head snapshot.")
        
        # 从缓存中获取当前的头快照
        head_snapshot = self._snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot:
             raise ValueError(f"Head snapshot {sandbox.head_snapshot_id} not found.")

        # 创建一个可变的 moment 副本以进行安全修改
        mutable_moment = deepcopy(dict(head_snapshot.moment))
        new_moment_data = update_function(mutable_moment)

        # 基于修改后的 moment 创建一个新的快照对象
        new_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            moment=new_moment_data,
            parent_snapshot_id=sandbox.head_snapshot_id,
            triggering_input={"source": "editor_moment_update"}
        )
        
        # 添加 await，确保新快照被异步写入文件系统
        await self._snapshot_store.save(new_snapshot)
        
        # 更新沙盒的头指针，使其指向新的快照
        sandbox.head_snapshot_id = new_snapshot.id
        
        # 添加 await，确保持有新头指针的沙盒对象也被异步持久化
        await self._sandbox_store.save(sandbox)
        
        logger.info(f"Created new snapshot {new_snapshot.id} and persisted all changes for sandbox {sandbox.id}.")
        return sandbox