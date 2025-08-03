# plugins/core_persistence/models.py

from enum import Enum

# --- 文件约定 (插件内部实现细节) ---
class AssetType(str, Enum):
    GRAPH = "graph"
    CODEX = "codex"
    SANDBOX = "sandbox"

FILE_EXTENSIONS = {
    AssetType.GRAPH: ".graph.hevno.json",
    AssetType.CODEX: ".codex.hevno.json",
}
