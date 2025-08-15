# plugins/core_engine/editor_utils.py
import logging
from copy import deepcopy
from uuid import UUID
from typing import Callable, Dict, Any, List

from fastapi import HTTPException

from .contracts import (
    Sandbox, EditorUtilsServiceInterface, SnapshotStoreInterface, StateSnapshot,
    SandboxStoreInterface, Mutation
)
# 确保从 contracts 导入 Mutation
from .contracts import Mutation
from backend.core.utils import _navigate_to_sub_path, unwrap_dot_accessible_dicts

logger = logging.getLogger(__name__)

class EditorUtilsService(EditorUtilsServiceInterface):
    def __init__(self, sandbox_store: SandboxStoreInterface, snapshot_store: SnapshotStoreInterface):
        self._sandbox_store = sandbox_store
        self._snapshot_store = snapshot_store

    async def execute_mutations(self, sandbox: Sandbox, mutations: List[Mutation]) -> Sandbox:
        """
        【已重构】
        以原子方式执行一批修改操作。此版本简化了逻辑，确保缓存一致性。
        """
        # 1. 在操作开始时，立即创建一份沙盒的深拷贝。所有修改都将应用于这份拷贝。
        #    这可以防止直接修改缓存中的原始对象，保证了操作的原子性。
        sandbox_to_modify = sandbox.model_copy(deep=True)
        
        # 标志位，用于判断是否需要保存沙盒对象本身
        sandbox_state_changed = False

        # 2. 将修改按其目标作用域进行分组
        moment_mutations = []
        other_mutations = []
        for m in mutations:
            if m.path.startswith("moment/"):
                moment_mutations.append(m)
            elif m.path.startswith("definition/") or m.path.startswith("lore/"):
                other_mutations.append(m)
            else:
                raise ValueError(f"Invalid mutation path root: '{m.path}'. Must start with 'moment/', 'lore/', or 'definition/'.")

        # --- 阶段 1: 处理对 Sandbox (definition/lore) 的直接修改 ---
        if other_mutations:
            try:
                for m in other_mutations:
                    # 直接在可变的拷贝上应用修改
                    self._apply_single_mutation(sandbox_to_modify, m)
                sandbox_state_changed = True
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.error(f"Failed to apply mutation to sandbox {sandbox.id}: {e}", exc_info=True)
                raise ValueError(f"Mutation failed: {e}")
        
        # --- 阶段 2: 处理对 Moment 的修改 ---
        if moment_mutations:
            # 检查所有 moment 修改是否使用相同的 mutation_mode
            first_mode = moment_mutations[0].mutation_mode
            if not all(m.mutation_mode == first_mode for m in moment_mutations):
                raise ValueError("All mutations targeting 'moment' in a single request must use the same 'mutation_mode'.")

            if not sandbox_to_modify.head_snapshot_id:
                raise ValueError("Cannot mutate moment: Sandbox has no head snapshot.")
            
            head_snapshot = self._snapshot_store.get(sandbox_to_modify.head_snapshot_id)
            if not head_snapshot:
                 raise ValueError(f"Head snapshot {sandbox_to_modify.head_snapshot_id} not found.")

            # 深拷贝 moment 数据以进行安全修改
            mutable_moment = deepcopy(dict(head_snapshot.moment))
            try:
                 for m in moment_mutations:
                     self._apply_single_mutation(mutable_moment, m)
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.error(f"Failed to apply mutation to moment for sandbox {sandbox.id}: {e}", exc_info=True)
                raise ValueError(f"Mutation failed: {e}")

            # 根据模式决定是覆盖保存还是创建新快照
            if first_mode == "DIRECT":
                mutated_snapshot = head_snapshot.model_copy(update={"moment": mutable_moment})
                await self._snapshot_store.save(mutated_snapshot)
                logger.info(f"Directly mutated snapshot {head_snapshot.id}.")
            else: # mode == "SNAPSHOT"
                new_snapshot = StateSnapshot(
                    sandbox_id=sandbox.id,
                    moment=mutable_moment,
                    parent_snapshot_id=sandbox_to_modify.head_snapshot_id
                )
                await self._snapshot_store.save(new_snapshot)
                # 修改沙盒拷贝的头指针
                sandbox_to_modify.head_snapshot_id = new_snapshot.id
                sandbox_state_changed = True # 头指针已改变，需要保存沙盒
                logger.info(f"Created new snapshot {new_snapshot.id} for sandbox {sandbox.id}.")

        # --- 阶段 3: 如果有任何对沙盒状态的修改，则进行持久化 ---
        if sandbox_state_changed:
            await self._sandbox_store.save(sandbox_to_modify)

        # 4. 返回经过所有修改的、最新的沙盒对象
        return sandbox_to_modify

    def _apply_single_mutation(self, root_obj: Any, mutation: Mutation):
        path_parts = mutation.path.split('/')
        scope = path_parts[0]
        sub_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else ""

        current_level = root_obj
        if isinstance(root_obj, Sandbox):
             current_level = getattr(root_obj, scope)
        
        if not sub_path:
            if mutation.type == 'UPSERT':
                if not isinstance(mutation.value, dict):
                    raise TypeError(f"Cannot replace a scope root with a non-dictionary value for path '{mutation.path}'.")
                current_level.clear()
                current_level.update(mutation.value)
                return
            else:
                raise ValueError(f"Operation '{mutation.type}' on a scope root ('{mutation.path}') is not supported.")

        parent, key = _navigate_to_sub_path(current_level, sub_path, create_if_missing=(mutation.type == 'UPSERT'))
        
        if mutation.type == 'UPSERT':
            parent[key] = mutation.value
        elif mutation.type == 'DELETE':
            try:
                if isinstance(parent, list) and isinstance(key, int):
                    del parent[key]
                elif isinstance(parent, dict):
                    del parent[key]
                else:
                    # _navigate_to_sub_path 应该已经处理了路径不存在的错误，但这里再加一层保险
                    raise KeyError
            except (KeyError, IndexError):
                 raise KeyError(f"Resource at path '{mutation.path}' not found for deletion.")
        elif mutation.type == 'LIST_APPEND':
            target_list = parent.get(key) if isinstance(parent, dict) else parent[key]
            if not isinstance(target_list, list):
                raise TypeError(f"Cannot use LIST_APPEND on a non-list object at path '{mutation.path}'.")
            target_list.append(mutation.value)

    async def execute_queries(self, sandbox: Sandbox, paths: List[str]) -> Dict[str, Any]:
        results = {}
        moment_data = None
        
        if any(p == 'moment' or p.startswith("moment/") for p in paths):
            if sandbox.head_snapshot_id:
                head_snapshot = self._snapshot_store.get(sandbox.head_snapshot_id)
                if head_snapshot:
                    moment_data = head_snapshot.moment
            if moment_data is None:
                moment_data = {}

        for path in paths:
            path_parts = path.split('/')
            scope = path_parts[0]
            sub_path = '/'.join(path_parts[1:])

            root_obj = None
            if scope == 'moment':
                root_obj = moment_data
            elif scope == 'lore':
                root_obj = sandbox.lore
            elif scope == 'definition':
                root_obj = sandbox.definition
            else:
                results[path] = None
                continue
            
            if root_obj is None:
                results[path] = None
                continue

            if not sub_path:
                results[path] = unwrap_dot_accessible_dicts(root_obj)
                continue

            try:
                parent, key = _navigate_to_sub_path(root_obj, sub_path)
                value = parent[key]
                results[path] = unwrap_dot_accessible_dicts(value)
            except (HTTPException, KeyError, IndexError, TypeError):
                results[path] = None
        
        return results