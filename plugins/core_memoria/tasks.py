# plugins/core_memoria/tasks.py
import logging
from typing import List, Dict, Any

from backend.core.contracts import (
    Container, 
    Sandbox, 
    StateSnapshot,
    SnapshotStoreInterface,
    BackgroundTaskManager
)
from .models import MemoryEntry, MemoryStream, Memoria, AutoSynthesisConfig
from plugins.core_llm.service import LLMService
from plugins.core_llm.models import LLMResponse, LLMRequestFailedError


logger = logging.getLogger(__name__)

async def run_synthesis_task(
    container: Container,
    sandbox_id: str,
    stream_name: str,
    synthesis_config: Dict[str, Any],
    entries_to_summarize_dicts: List[Dict[str, Any]]
):
    """
    一个后台任务，负责调用 LLM 生成总结，并创建一个新的状态快照。
    """
    logger.info(f"后台任务启动：为沙盒 {sandbox_id} 的流 '{stream_name}' 生成总结。")
    
    try:
        # --- 1. 解析服务和数据 ---
        llm_service: LLMService = container.resolve("llm_service")
        sandbox_store: Dict = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")

        config = AutoSynthesisConfig.model_validate(synthesis_config)
        entries_to_summarize = [MemoryEntry.model_validate(d) for d in entries_to_summarize_dicts]

        # --- 2. 调用 LLM ---
        events_text = "\n".join([f"- {entry.content}" for entry in entries_to_summarize])
        prompt = config.prompt.format(events_text=events_text)

        response: LLMResponse = await llm_service.request(model_name=config.model, prompt=prompt)

        if response.status != "success" or not response.content:
            error_msg = response.error_details.message if response.error_details else 'No content'
            logger.error(f"LLM 总结失败 for sandbox {sandbox_id}: {error_msg}")
            return

        summary_content = response.content.strip()
        logger.info(f"LLM 成功生成总结 for sandbox {sandbox_id} a stream '{stream_name}'.")

        # --- 3. 更新世界状态（通过创建新快照）---
        # 这是关键部分，它以不可变的方式更新世界
        sandbox: Sandbox = sandbox_store.get(sandbox_id)
        if not sandbox or not sandbox.head_snapshot_id:
            logger.error(f"在后台任务中找不到沙盒 {sandbox_id} 或其头快照。")
            return

        head_snapshot = snapshot_store.get(sandbox.head_snapshot_id)
        if not head_snapshot:
            logger.error(f"数据不一致：找不到沙盒 {sandbox_id} 的头快照 {sandbox.head_snapshot_id}。")
            return
        
        # 创建一个新的、可变的 world_state 副本，保留所有其他状态
        new_world_state = head_snapshot.world_state.copy()
        memoria_data = new_world_state.get("memoria", {})
        
        memoria = Memoria.model_validate(memoria_data)
        stream = memoria.get_stream(stream_name)
        if not stream:
            # 这理论上不应该发生，因为触发任务时流必然存在
            logger.warning(f"在后台任务中，流 '{stream_name}' 在 world.memoria 中消失了。")
            return

        stream.synthesis_trigger_counter = 0

        # 创建并添加新的总结条目
        summary_entry = MemoryEntry(
            sequence_id=memoria.get_next_sequence_id(),
            level=config.level,
            tags=["synthesis", "auto-generated"],
            content=summary_content
        )
        stream.entries.append(summary_entry)
        memoria.set_stream(stream_name, stream)

        # 将更新后的 memoria 数据写回到 new_world_state 的 'memoria' 键下
        new_world_state["memoria"] = memoria.model_dump()

        # 创建一个全新的快照，使用完整的、更新后的 new_world_state
        new_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            graph_collection=head_snapshot.graph_collection,
            world_state=new_world_state,
            parent_snapshot_id=head_snapshot.id,
            triggering_input={"_system_event": "memoria_synthesis", "stream": stream_name}
        )
        
        # 保存新快照并更新沙盒的头指针
        snapshot_store.save(new_snapshot)
        sandbox.head_snapshot_id = new_snapshot.id
        logger.info(f"为沙盒 {sandbox_id} 创建了新的头快照 {new_snapshot.id}，包含新总结。")

    except LLMRequestFailedError as e:
        logger.error(f"后台 LLM 请求在多次重试后失败: {e}", exc_info=False)
    except Exception as e:
        logger.exception(f"在执行 memoria 综合任务时发生未预料的错误: {e}")