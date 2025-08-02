# plugins/example_logger/hooks.py
import logging
from datetime import datetime, timezone
from backend.core.contracts import EngineStepStartContext, BeforeSnapshotCreateContext

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
    一个过滤型钩子实现，用于向每个创建的快照的 world_state 中添加自定义元数据。
    """
    world_state = snapshot_data.get("world_state", {})
    if "plugin_metadata" not in world_state:
        world_state["plugin_metadata"] = {}
        
    world_state["plugin_metadata"]["example_logger"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "This snapshot was processed by the example_logger plugin."
    }
    
    snapshot_data["world_state"] = world_state
    
    return snapshot_data
