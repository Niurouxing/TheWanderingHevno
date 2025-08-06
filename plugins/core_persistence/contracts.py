# plugins/core_persistence/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TypeVar, List, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timezone

T = TypeVar('T', bound=BaseModel)

# --- 共享数据模型 (从 models.py 移动而来) ---

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


# --- 服务接口 ---

class PersistenceServiceInterface(ABC):
    @abstractmethod
    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel], base_image_bytes: Optional[bytes] = None) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def import_package(self, zip_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str], bytes]:
        raise NotImplementedError
    
    @abstractmethod
    def save_sandbox_icon(self, sandbox_id: str, icon_bytes: bytes) -> 'Path':
        raise NotImplementedError

    @abstractmethod
    def get_sandbox_icon_path(self, sandbox_id: str) -> Optional['Path']:
        raise NotImplementedError
    
    @abstractmethod
    def get_default_icon_path(self) -> 'Path':
        raise NotImplementedError