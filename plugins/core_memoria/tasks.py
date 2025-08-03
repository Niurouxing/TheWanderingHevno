# plugins/core_memoria/tasks.py 
import logging
from typing import List, Dict, Any
from uuid import UUID

# 从平台核心导入接口和类型
from backend.core.contracts import Container
# 从本插件导入模型
from .models import AutoSynthesisConfig

from plugins.core_llm.contracts import (
    LLMServiceInterface, 
    LLMResponse, 
    LLMRequestFailedError,
    LLMResponseStatus
)

logger = logging.getLogger(__name__)

async def run_synthesis_task(
    container: Container,
    sandbox_id: UUID,
    stream_name: str,
    synthesis_config: Dict[str, Any],
    entries_to_summarize_dicts: List[Dict[str, Any]]
):
    """
    一个解耦的后台任务。
    """
    logger.info(f"后台任务启动：为沙盒 {sandbox_id} 的流 '{stream_name}' 生成总结。")
    
    try:
        # --- 1. 解析需要的服务和数据 ---
        llm_service: LLMServiceInterface = container.resolve("llm_service")
        event_queue: Dict[UUID, List[Dict[str, Any]]] = container.resolve("memoria_event_queue")
        config = AutoSynthesisConfig.model_validate(synthesis_config)

        # --- 2. 准备并调用 LLM ---
        events_text = "\n".join([f"- {entry['content']}" for entry in entries_to_summarize_dicts])
        prompt = config.prompt.format(events_text=events_text)

        response: LLMResponse = await llm_service.request(model_name=config.model, prompt=prompt)

        if response.status != LLMResponseStatus.SUCCESS or not response.content:
            error_msg = response.error_details.message if response.error_details else 'No content'
            logger.error(f"LLM 总结失败 for sandbox {sandbox_id}: {error_msg}")
            return

        summary_content = response.content.strip()
        logger.info(f"LLM 成功生成总结 for sandbox {sandbox_id} of stream '{stream_name}'.")

        event_payload = {
            "type": "memoria_synthesis_completed",
            "stream_name": stream_name,
            "content": summary_content,
            "level": config.level,
            "tags": ["synthesis", "auto-generated"],
        }
        
        if sandbox_id not in event_queue:
            event_queue[sandbox_id] = []
        event_queue[sandbox_id].append(event_payload)
        
        logger.info(f"已为沙盒 {sandbox_id} 成功提交 'memoria_synthesis_completed' 事件。")

    except LLMRequestFailedError as e:
        logger.error(f"后台 LLM 请求在多次重试后失败: {e}", exc_info=False)
    except Exception:
        logger.exception(f"在执行 memoria 综合任务时发生未预料的错误 for sandbox {sandbox_id}")