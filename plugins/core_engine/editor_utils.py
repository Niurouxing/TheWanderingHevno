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
from .contracts import Mutation, MutateResourceRequest 
from backend.core.utils import _navigate_to_sub_path, unwrap_dot_accessible_dicts

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

class EditorUtilsService(EditorUtilsServiceInterface):
    def __init__(self, sandbox_store: SandboxStoreInterface, snapshot_store: SnapshotStoreInterface):
        self._sandbox_store = sandbox_store
        self._snapshot_store = snapshot_store
        # 在这里为未来添加锁预留了位置
        # self._locks = defaultdict(asyncio.Lock)

    async def execute_mutations(self, sandbox: Sandbox, mutations: List[Mutation]) -> Sandbox:
        """
        原子性地执行一批修改操作。
        """
        # 在这里获取锁 (暂缓)
        # async with self._locks[sandbox.id]:
        
        # 将修改按其写入目标进行分组
        # 对 definition/lore 的修改可以直接在沙盒对象上进行
        # 对 moment 的修改需要特殊处理
        sandbox_mutations = []
        moment_mutations = []

        for m in mutations:
            if m.path.startswith("moment/"):
                moment_mutations.append(m)
            elif m.path.startswith("definition/") or m.path.startswith("lore/"):
                sandbox_mutations.append(m)
            else:
                raise ValueError(f"Invalid mutation path root: '{m.path}'. Must start with 'moment/', 'lore/', or 'definition/'.")

        # --- 阶段1: 处理对 Sandbox (definition/lore) 的直接修改 ---
        if sandbox_mutations:
            # 深拷贝以支持失败时回滚（尽管目前是直接修改）
            sandbox_clone = sandbox.model_copy(deep=True)
            try:
                for m in sandbox_mutations:
                    self._apply_single_mutation(sandbox_clone, m)
                # 应用修改
                sandbox = sandbox_clone
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.error(f"Failed to apply mutation to sandbox {sandbox.id}: {e}", exc_info=True)
                raise ValueError(f"Mutation failed: {e}")
        
        # --- 阶段2: 处理对 Moment 的修改 ---
        if moment_mutations:
            # 检查所有moment修改是否使用相同的 mutation_mode，这是原子性的要求
            first_mode = moment_mutations[0].mutation_mode
            if not all(m.mutation_mode == first_mode for m in moment_mutations):
                raise ValueError("All mutations targeting 'moment' in a single request must use the same 'mutation_mode'.")

            if not sandbox.head_snapshot_id:
                raise ValueError("Cannot mutate moment: Sandbox has no head snapshot.")
            
            head_snapshot = self._snapshot_store.get(sandbox.head_snapshot_id)
            if not head_snapshot:
                 raise ValueError(f"Head snapshot {sandbox.head_snapshot_id} not found.")

            # 深拷贝 moment 数据以进行安全修改
            mutable_moment = deepcopy(dict(head_snapshot.moment))
            try:
                 for m in moment_mutations:
                     # 传入 moment 字典作为根进行修改
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
                    parent_snapshot_id=sandbox.head_snapshot_id
                )
                await self._snapshot_store.save(new_snapshot)
                sandbox.head_snapshot_id = new_snapshot.id
                logger.info(f"Created new snapshot {new_snapshot.id} for sandbox {sandbox.id}.")

        # --- 阶段3: 持久化沙盒的最终状态 ---
        # 如果 definition/lore 或 head_snapshot_id 被修改，保存沙盒
        if sandbox_mutations or any(m.mutation_mode == "SNAPSHOT" for m in moment_mutations):
            await self._sandbox_store.save(sandbox)

        return sandbox

    def _apply_single_mutation(self, root_obj: Any, mutation: Mutation):
        path_parts = mutation.path.split('/')
        scope = path_parts[0]

        # 健壮性改进，处理对作用域根的操作
        sub_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else ""

        current_level = root_obj
        if isinstance(root_obj, Sandbox):
             current_level = getattr(root_obj, scope)
        
        # 如果子路径为空，说明操作的是作用域根本身
        if not sub_path:
            if mutation.type == 'UPSERT':
                # 这等同于替换整个作用域，需要确保 value 是字典
                if not isinstance(mutation.value, dict):
                    raise TypeError(f"Cannot replace a scope root with a non-dictionary value for path '{mutation.path}'.")
                # 清空并更新
                current_level.clear()
                current_level.update(mutation.value)
                return
            else:
                raise ValueError(f"Operation '{mutation.type}' on a scope root ('{mutation.path}') is not supported. Use a sub-path.")

        # 导航到父级对象和最终的键 
        parent, key = _navigate_to_sub_path(current_level, sub_path, create_if_missing=(mutation.type == 'UPSERT'))
        if mutation.type == 'UPSERT':
            parent[key] = mutation.value
        elif mutation.type == 'DELETE':
            if isinstance(parent, dict) and key in parent:
                del parent[key]
            elif isinstance(parent, list) and isinstance(key, int) and 0 <= key < len(parent):
                del parent[key]
            else:
                raise KeyError(f"Resource at path '{mutation.path}' not found for deletion.")
        elif mutation.type == 'LIST_APPEND':
            target_list = parent[key]
            if not isinstance(target_list, list):
                raise TypeError(f"Cannot use LIST_APPEND on a non-list object at path '{mutation.path}'.")
            target_list.append(mutation.value)

    async def execute_queries(self, sandbox: Sandbox, paths: List[str]) -> Dict[str, Any]:
        results = {}
        
        # 为了效率，我们只加载一次头快照（如果需要的话）
        moment_data = None
        
        # --- [FIXED] ---
        # 修正了条件，使其能正确处理对根作用域 "moment" 的请求
        if any(p == 'moment' or p.startswith("moment/") for p in paths):
            if sandbox.head_snapshot_id:
                head_snapshot = self._snapshot_store.get(sandbox.head_snapshot_id)
                if head_snapshot:
                    moment_data = head_snapshot.moment
            # 如果没有快照或未找到，moment_data 保持为 None，后续逻辑会处理
            if moment_data is None:
                # 即使找不到快照，也初始化为空字典，以防后续代码出错
                moment_data = {}

        for path in paths:
            path_parts = path.split('/')
            scope = path_parts[0]
            sub_path = '/'.join(path_parts[1:])

            root_obj = None
            if scope == 'moment':
                # 现在这里可以正确获取到加载的数据
                root_obj = moment_data
            elif scope == 'lore':
                root_obj = sandbox.lore
            elif scope == 'definition':
                root_obj = sandbox.definition
            else:
                # 如果 scope 无效，直接将结果设为 null
                results[path] = None
                continue
            
            # 如果 root_obj 本身就是 None（比如 moment 加载失败），直接返回
            if root_obj is None:
                results[path] = None
                continue

            # 如果路径指向的是整个作用域
            if not sub_path:
                results[path] = unwrap_dot_accessible_dicts(root_obj)
                continue

            try:
                # 注意: _navigate_to_sub_path 需要 root_obj 是字典或类似字典的对象
                parent, key = _navigate_to_sub_path(root_obj, sub_path)
                value = parent[key]
                results[path] = unwrap_dot_accessible_dicts(value)
            except (HTTPException, KeyError, IndexError, TypeError):
                # 如果路径查找失败，将结果设为 null
                results[path] = None
        
        return results