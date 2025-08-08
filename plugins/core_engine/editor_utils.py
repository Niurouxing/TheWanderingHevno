# plugins/core_engine/editor_utils.py
import logging
from copy import deepcopy
from uuid import UUID
from typing import Callable, Dict, Any

from .contracts import Sandbox, StateSnapshot, SnapshotStoreInterface, EditorUtilsServiceInterface

logger = logging.getLogger(__name__)

class EditorUtilsService(EditorUtilsServiceInterface):
    
    def perform_sandbox_update(self, sandbox: Sandbox, update_function: Callable[[Sandbox], None]) -> Sandbox:
        """
        直接在 Sandbox 对象上执行一个修改函数。
        此函数用于对 'definition' 和 'lore' 作用域进行“创作式”修改。
        它不创建新的快照。
        """
        update_function(sandbox)
        logger.debug(f"Performed direct update on Sandbox '{sandbox.id}'.")
        return sandbox

    def perform_live_moment_update(
        self,
        sandbox: Sandbox,
        snapshot_store: SnapshotStoreInterface,
        update_function: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Sandbox:
        """
        安全地修改当前沙盒的 'moment' 状态，这必须创建一个新的历史快照。
        """
        if not sandbox.head_snapshot_id:
            raise ValueError("Cannot update moment: Sandbox has no head snapshot.")
        
        head_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot:
            raise ValueError(f"Head snapshot {sandbox.head_snapshot_id} not found in store.")

        mutable_moment = deepcopy(dict(head_snapshot.moment))
        new_moment_data = update_function(mutable_moment)

        new_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            moment=new_moment_data,
            parent_snapshot_id=sandbox.head_snapshot_id,
            triggering_input={"source": "editor_moment_update"}
        )
        
        snapshot_store.save(new_snapshot)
        sandbox.head_snapshot_id = new_snapshot.id
        
        logger.info(f"Created new snapshot {new_snapshot.id} for sandbox {sandbox.id} due to editor moment update.")
        return sandbox