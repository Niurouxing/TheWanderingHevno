# plugins/core_remote_hooks/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List

class HookLocation(Enum):
    """
    定义一个钩子实现的位置，用于智能路由。
    """
    LOCAL = "local"    # 仅在当前环境（后端）中实现
    REMOTE = "remote"  # 仅在远端环境（前端）中实现
    BOTH = "both"      # 在两个环境中都有实现
    UNKNOWN = "unknown"  # 未在任何注册表中找到

class RemoteHookEmitterInterface(ABC):
    """
    定义了将钩子事件发送到远端（前端）的能力。
    """
    @abstractmethod
    async def emit(self, hook_name: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

class GlobalHookRegistryInterface(ABC):
    """
    定义了全域钩子路由表的接口。
    """
    @abstractmethod
    def register_backend_hooks(self, hooks: List[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_frontend_hooks(self, hooks: List[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_hook_location(self, hook_name: str) -> HookLocation:
        raise NotImplementedError