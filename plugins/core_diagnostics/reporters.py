# plugins/core_diagnostics/reporters.py

from typing import Any, List, Dict
from .contracts import Reportable

class PluginReporter(Reportable):
    
    def __init__(self, loaded_manifests: List[Dict[str, Any]]):
        self._manifests = loaded_manifests

    @property
    def report_key(self) -> str:
        return "plugins"
    
    async def generate_report(self) -> Any:
        # 按类型对插件清单进行分类
        backend_plugins = [
            manifest for manifest in self._manifests if "backend" in manifest
        ]
        frontend_plugins = [
            manifest for manifest in self._manifests if "frontend" in manifest
        ]
        
        return {
            "backend": backend_plugins,
            "frontend": frontend_plugins
        }