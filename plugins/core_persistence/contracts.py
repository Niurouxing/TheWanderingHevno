# plugins/core_persistence/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TypeVar, List, Any, Optional
from uuid import UUID
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timezone

# 不再从 core_engine.contracts 导入 Sandbox 和 StateSnapshot
# from plugins.core_engine.contracts import Sandbox, StateSnapshot

T = TypeVar('T', bound=BaseModel)

# --- 共享数据模型 (Package/Manifest) ---

class PackageType(str, Enum):
    """定义了可以被导入/导出的不同类型的包。"""
    SANDBOX_ARCHIVE = "sandbox_archive"
    GRAPH_COLLECTION = "graph_collection"
    CODEX_COLLECTION = "codex_collection"

class PluginRequirement(BaseModel):
    """描述包所依赖的插件。"""
    name: str = Field(..., description="Plugin identifier, e.g., 'hevno-dice-roller'")
    source_url: str = Field(..., description="Plugin source, e.g., 'https://github.com/user/repo'")
    version: str = Field(..., description="Compatible version or Git ref")

class PackageManifest(BaseModel):
    """
    定义了 .hevno.zip 包内容的标准清单。
    这是核心的共享数据模型。
    """
    format_version: str = Field(default="1.0")
    package_type: PackageType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_point: str
    required_plugins: List[PluginRequirement] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# --- 服务接口 (合并并异步化) ---

class PersistenceServiceInterface(ABC):
    """
    定义了核心持久化服务的文件系统I/O能力。
    注意：它不再知道 Sandbox 或 StateSnapshot 的具体模型，
    而是处理通用的字典数据，使得依赖关系更清晰。
    """

    # --- 沙盒持久化方法 ---
    @abstractmethod
    async def save_sandbox(self, sandbox_id: UUID, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def load_sandbox(self, sandbox_id: UUID) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def delete_sandbox(self, sandbox_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_sandbox_ids(self) -> List[str]:
        raise NotImplementedError

    # --- 快照持久化方法 ---
    @abstractmethod
    async def save_snapshot(self, sandbox_id: UUID, snapshot_id: UUID, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def load_snapshot(self, sandbox_id: UUID, snapshot_id: UUID) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def load_all_snapshots_for_sandbox(self, sandbox_id: UUID) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def delete_all_for_sandbox(self, sandbox_id: UUID) -> None:
        raise NotImplementedError
    
    # --- 包导入/导出方法 ---
    @abstractmethod
    async def export_package(self, manifest: PackageManifest, data_files: Dict[str, Any], base_image_bytes: Optional[bytes] = None) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def import_package(self, package_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str], bytes]:
        raise NotImplementedError
    
    # --- 沙盒图标处理方法 ---
    @abstractmethod
    async def save_sandbox_icon(self, sandbox_id: str, icon_bytes: bytes) -> Path:
        raise NotImplementedError

    @abstractmethod
    def get_sandbox_icon_path(self, sandbox_id: str) -> Optional[Path]:
        raise NotImplementedError
    
    @abstractmethod
    def get_default_icon_path(self) -> Path:
        raise NotImplementedError

    @property
    @abstractmethod
    def sandboxes_root_dir(self) -> Path:
        raise NotImplementedError

    @abstractmethod
    async def delete_snapshot(self, sandbox_id: UUID, snapshot_id: UUID) -> None:
        """异步删除一个指定的快照文件。"""
        raise NotImplementedError