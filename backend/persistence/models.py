# backend/persistence/models.py (新文件)

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# --- 文件约定 ---
# 在一个中心位置定义，方便整个应用引用
class AssetType(str, Enum):
    GRAPH = "graph"
    CODEX = "codex"
    SANDBOX = "sandbox"

FILE_EXTENSIONS = {
    AssetType.GRAPH: ".graph.hevno.json",
    AssetType.CODEX: ".codex.hevno.json",
}

# --- 插件占位符模型 (为未来预留) ---
class PluginRequirement(BaseModel):
    """
    描述一个必需的插件依赖。
    这个模型现在是占位符，但在依赖检查阶段会变得至关重要。
    """
    name: str = Field(..., description="插件的唯一标识符, e.g., 'hevno-dice-roller'")
    source_url: str = Field(..., description="插件的来源, e.g., 'https://github.com/alice/hevno-dice-roller'")
    version: str = Field(..., description="兼容的版本或 Git 引用 (commit hash, tag, or branch)")

# --- 包清单模型 ---
class PackageType(str, Enum):
    """定义导出的包的类型。"""
    SANDBOX_ARCHIVE = "sandbox_archive"
    GRAPH_COLLECTION = "graph_collection"
    CODEX_COLLECTION = "codex_collection"

class PackageManifest(BaseModel):
    """
    定义 .hevno.zip 包中 manifest.json 的结构。
    这是包的“身份证”，描述了其内容和要求。
    """
    format_version: str = Field(default="1.0", description="清单格式的版本。")
    package_type: PackageType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_point: str = Field(..., description="指向包内主数据文件的相对路径, e.g., 'data/sandbox.json' or 'data/main.graph.hevno.json'")
    
    # 【核心扩展点】为插件系统预留的依赖声明
    required_plugins: List[PluginRequirement] = Field(
        default_factory=list,
        description="运行此包内容所需的插件列表。"
    )
    # 也可以在这里添加作者、描述等元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)