# plugins/core_remote_hooks/registry.py

import logging
from typing import List, Set
from .contracts import GlobalHookRegistryInterface, HookLocation

logger = logging.getLogger(__name__)

class GlobalHookRegistry(GlobalHookRegistryInterface):
    """
    一个中心化的单例服务，用于存储和管理全域钩子路由表。
    """
    def __init__(self):
        self._backend_hooks: Set[str] = set()
        self._frontend_hooks: Set[str] = set()
        logger.info("GlobalHookRegistry initialized.")

    def register_backend_hooks(self, hooks: List[str]) -> None:
        """注册所有在后端发现的钩子。"""
        count_before = len(self._backend_hooks)
        self._backend_hooks.update(hooks)
        count_after = len(self._backend_hooks)
        logger.info(f"Registered {count_after - count_before} new backend hooks. Total: {count_after}.")

    def register_frontend_hooks(self, hooks: List[str]) -> None:
        """在收到前端同步消息后，注册所有前端钩子。"""
        count_before = len(self._frontend_hooks)
        self._frontend_hooks.update(hooks)
        count_after = len(self._frontend_hooks)
        logger.info(f"Registered {count_after - count_before} new frontend hooks from remote sync. Total: {count_after}.")

    def get_hook_location(self, hook_name: str) -> HookLocation:
        """根据钩子名称，查询其在全栈中的位置。"""
        is_local = hook_name in self._backend_hooks
        is_remote = hook_name in self._frontend_hooks

        if is_local and is_remote:
            return HookLocation.BOTH
        if is_local:
            return HookLocation.LOCAL
        if is_remote:
            return HookLocation.REMOTE
        
        return HookLocation.UNKNOWN