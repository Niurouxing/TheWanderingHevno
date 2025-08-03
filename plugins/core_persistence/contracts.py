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
    """
    定义了持久化服务必须提供的核心能力的抽象接口。
    其他插件应该依赖于这个接口，而不是具体的 PersistenceService 类。
    """

    @abstractmethod
    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel]) -> bytes:
        """
        在内存中创建一个 .hevno.zip 包并返回其字节流。
        """
        raise NotImplementedError

    @abstractmethod
    def import_package(self, zip_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str]]:
        """
        解压包，读取清单和所有数据文件（作为原始字符串）。
        """
        raise NotImplementedError
    
    # 我们可以选择性地将其他方法也加入接口，如果未来有其他插件需要
    # from .models import AssetType
    # @abstractmethod
    # def list_assets(self, asset_type: AssetType) -> List[str]:
    #     raise NotImplementedError