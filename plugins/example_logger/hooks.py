# plugins/example_logger/hooks.py
import logging
from datetime import datetime, timezone
from backend.core.plugin_types import EngineStepStartContext, BeforeSnapshotCreateContext

logger = logging.getLogger(__name__)

async def on_engine_step_start(context: EngineStepStartContext) -> None:
    """
    一个通知型钩子实现，用于在引擎每次执行时打印日志。
    """
    logger.info(
        f"PLUGIN-HOOK: Engine step started for sandbox "
        f"{context.initial_snapshot.sandbox_id} "
        f"with trigger input: {context.triggering_input}"
    )

async def on_before_snapshot_create(
    snapshot_data: dict, 
    context: BeforeSnapshotCreateContext
) -> dict:
    """
    一个过滤型钩子实现，用于向每个创建的快照中添加自定义元数据。
    """
    logger.info(f"PLUGIN-HOOK: Filtering snapshot data for sandbox {context.snapshot_data['sandbox_id']}")
    
    if "plugin_metadata" not in snapshot_data:
        snapshot_data["plugin_metadata"] = {}
        
    snapshot_data["plugin_metadata"]["example_logger"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "This snapshot was processed by the example_logger plugin."
    }
    
    # 必须返回修改后的数据
    return snapshot_data