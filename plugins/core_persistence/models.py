# plugins/core_persistence/models.py

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# --- 文件约定 ---
class AssetType(str, Enum):
    GRAPH = "graph"
    CODEX = "codex"
    SANDBOX = "sandbox"

FILE_EXTENSIONS = {
    AssetType.GRAPH: ".graph.hevno.json",
    AssetType.CODEX: ".codex.hevno.json",
}

# --- 插件占位符模型 ---
class PluginRequirement(BaseModel):
    name: str = Field(..., description="Plugin identifier, e.g., 'hevno-dice-roller'")
    source_url: str = Field(..., description="Plugin source, e.g., 'https://github.com/user/repo'")
    version: str = Field(..., description="Compatible version or Git ref")

# --- 包清单模型 ---
class PackageType(str, Enum):
    SANDBOX_ARCHIVE = "sandbox_archive"
    GRAPH_COLLECTION = "graph_collection"
    CODEX_COLLECTION = "codex_collection"

class PackageManifest(BaseModel):
    format_version: str = Field(default="1.0")
    package_type: PackageType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_point: str
    required_plugins: List[PluginRequirement] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)