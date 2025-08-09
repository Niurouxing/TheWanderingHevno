# plugins/core_persistence/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TypeVar, List, Any, Optional
from uuid import UUID
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timezone

# 导入依赖的数据模型
from plugins.core_engine.contracts import Sandbox, StateSnapshot

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
    【已合并和异步化】
    定义了核心持久化服务必须提供的所有能力，包括沙盒/快照的文件操作
    以及包的导入导出。所有涉及I/O的操作现在都是异步的。
    """

    # --- 沙盒持久化方法 ---
    @abstractmethod
    async def save_sandbox(self, sandbox: Sandbox) -> None:
        """异步保存一个沙盒对象到其本地文件中。"""
        raise NotImplementedError

    @abstractmethod
    async def load_sandbox(self, sandbox_id: UUID) -> Optional[Sandbox]:
        """异步从本地文件加载一个沙盒对象。"""
        raise NotImplementedError

    @abstractmethod
    async def delete_sandbox(self, sandbox_id: UUID) -> None:
        """异步删除一个沙盒及其所有相关文件（包括快照）。"""
        raise NotImplementedError

    @abstractmethod
    async def list_sandbox_ids(self) -> List[str]:
        """异步列出所有已存在沙盒的ID。"""
        raise NotImplementedError

    # --- 快照持久化方法 ---
    @abstractmethod
    async def save_snapshot(self, snapshot: StateSnapshot) -> None:
        """异步保存一个快照对象到其本地文件中。"""
        raise NotImplementedError

    @abstractmethod
    async def load_snapshot(self, sandbox_id: UUID, snapshot_id: UUID) -> Optional[StateSnapshot]:
        """异步从本地文件加载一个特定的快照对象。"""
        raise NotImplementedError

    @abstractmethod
    async def load_all_snapshots_for_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        """异步加载属于特定沙盒的所有快照。"""
        raise NotImplementedError
    
    # --- 包导入/导出方法 ---
    @abstractmethod
    async def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel], base_image_bytes: Optional[bytes] = None) -> bytes:
        """异步创建一个 .hevno.zip 包，嵌入PNG，并返回其字节流。"""
        raise NotImplementedError

    @abstractmethod
    async def import_package(self, package_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str], bytes]:
        """异步从PNG中解压包，返回清单、数据文件和原始PNG图像字节。"""
        raise NotImplementedError
    
    # --- 沙盒图标处理方法 (可以是同步或异步，但为保持一致性，设为异步) ---
    @abstractmethod
    async def save_sandbox_icon(self, sandbox_id: str, icon_bytes: bytes) -> Path:
        """异步保存沙盒图标文件。"""
        raise NotImplementedError

    @abstractmethod
    def get_sandbox_icon_path(self, sandbox_id: str) -> Optional[Path]:
        """获取沙盒图标的文件路径，如果不存在则返回None (此操作通常很快，可以是同步的)。"""
        raise NotImplementedError
    
    @abstractmethod
    def get_default_icon_path(self) -> Path:
        """获取默认图标的路径 (同步)。"""
        raise NotImplementedError