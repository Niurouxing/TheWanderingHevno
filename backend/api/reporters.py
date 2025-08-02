# backend/api/reporters.py
from typing import Dict, Any
from backend.core.reporting import Reportable

class SandboxStatsReporter(Reportable):
    # 接收 main.py 中的状态存储作为依赖
    def __init__(self, sandbox_store: Dict, snapshot_store):
        self._sandbox_store = sandbox_store
        self._snapshot_store = snapshot_store

    @property
    def report_key(self) -> str:
        return "system_stats"

    @property
    def is_static(self) -> bool:
        # 这是一个动态报告！
        return False

    async def generate_report(self) -> Any:
        # 每次调用都实时计算
        active_sandboxes = len(self._sandbox_store)
        total_snapshots = len(self._snapshot_store._store) # 假设可以访问内部存储
        
        # 甚至可以报告更复杂的信息
        graphs_in_use = set()
        for sandbox in self._sandbox_store.values():
            latest_snapshot = sandbox.get_latest_snapshot(self._snapshot_store)
            if latest_snapshot:
                graphs_in_use.update(latest_snapshot.graph_collection.root.keys())

        return {
            "active_sandbox_count": active_sandboxes,
            "total_snapshot_count": total_snapshots,
            "unique_graph_names_in_use": sorted(list(graphs_in_use))
        }