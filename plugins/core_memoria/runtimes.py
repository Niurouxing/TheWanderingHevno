# plugins/core_memoria/runtimes.py (已重构)

import logging
from typing import Dict, Any, List

from backend.core.contracts import BackgroundTaskManager 
from plugins.core_engine.contracts import ExecutionContext, RuntimeInterface

# 本地导入保持不变
from .models import Memoria, MemoryEntry
from .tasks import run_synthesis_task

logger = logging.getLogger(__name__)


class MemoriaAddRuntime(RuntimeInterface):
    """
    向指定的记忆流中添加一条新的记忆条目。
    数据现在被写入 context.shared.moment_state。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        stream_name = config.get("stream")
        content = config.get("content")
        if not stream_name or not content:
            raise ValueError("MemoriaAddRuntime requires 'stream' and 'content' in its config.")
        
        level = config.get("level", "event")
        tags = config.get("tags", [])
        
        # 从 moment_state 中获取或创建 memoria 数据
        memoria_data = context.shared.moment_state.setdefault("memoria", {"__global_sequence__": 0})
        
        if "__hevno_type__" not in memoria_data:
            memoria_data["__hevno_type__"] = "hevno/memoria"

        memoria = Memoria.model_validate(memoria_data)
        
        stream = memoria.get_stream(stream_name)
        if stream is None:
            from .models import MemoryStream
            stream = MemoryStream()

        new_entry = MemoryEntry(
            sequence_id=memoria.get_next_sequence_id(),
            level=level,
            tags=tags,
            content=str(content)
        )
        stream.entries.append(new_entry)
        stream.synthesis_trigger_counter += 1
        
        memoria.set_stream(stream_name, stream)
        
        context.shared.moment_state["memoria"] = memoria.model_dump()

        synth_config = stream.config.auto_synthesis
        if synth_config.enabled and stream.synthesis_trigger_counter >= synth_config.trigger_count:
            logger.info(f"流 '{stream_name}' 满足综合条件，正在提交后台任务。")
            
            task_manager: BackgroundTaskManager = context.shared.services.task_manager
            entries_to_summarize = stream.entries[-synth_config.trigger_count:]
            
            task_manager.submit_task(
                run_synthesis_task,
                sandbox_id=context.initial_snapshot.sandbox_id,
                stream_name=stream_name,
                synthesis_config=synth_config.model_dump(),
                entries_to_summarize_dicts=[e.model_dump() for e in entries_to_summarize]
            )
            # 注意：synthesis_trigger_counter 的重置现在在 `apply_pending_synthesis` 钩子中完成
            # 此处不再需要重置，以避免状态不一致

        return {"output": new_entry.model_dump()}


class MemoriaQueryRuntime(RuntimeInterface):
    """
    根据声明式条件从一个记忆流中检索条目。
    数据现在从 context.shared.moment_state 读取。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        stream_name = config.get("stream")
        if not stream_name:
            raise ValueError("MemoriaQueryRuntime requires a 'stream' name in its config.")

        # 从 moment_state 中读取 memoria 数据
        memoria_data = context.shared.moment_state.get("memoria", {})
        # -------------------

        memoria = Memoria.model_validate(memoria_data)
        stream = memoria.get_stream(stream_name)
        
        if not stream:
            return {"output": []}

        # --- 过滤逻辑 (保持不变) ---
        results = stream.entries
        
        levels_to_get = config.get("levels")
        if isinstance(levels_to_get, list):
            results = [entry for entry in results if entry.level in levels_to_get]

        tags_to_get = config.get("tags")
        if isinstance(tags_to_get, list):
            tags_set = set(tags_to_get)
            results = [entry for entry in results if tags_set.intersection(entry.tags)]

        latest_n = config.get("latest")
        if isinstance(latest_n, int):
            results.sort(key=lambda e: e.sequence_id)
            results = results[-latest_n:]
            
        order = config.get("order", "ascending")
        reverse = (order == "descending")
        results.sort(key=lambda e: e.sequence_id, reverse=reverse)

        return {"output": [entry.model_dump() for entry in results]}


class MemoriaAggregateRuntime(RuntimeInterface):
    """
    【保持不变】将一批记忆条目聚合成格式化的文本。
    此运行时只处理传入的配置，不直接与状态交互，因此无需修改。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        # ... (此函数的代码保持不变) ...
        entries_data = config.get("entries")
        template = config.get("template", "{content}")
        joiner = config.get("joiner", "\n\n")

        if not isinstance(entries_data, list):
            raise TypeError("MemoriaAggregateRuntime 'entries' field must be a list of memory entry objects.")
        
        formatted_parts = []
        for entry_dict in entries_data:
            # 简单的模板替换
            part = template.format(
                id=entry_dict.get('id', ''),
                sequence_id=entry_dict.get('sequence_id', ''),
                level=entry_dict.get('level', ''),
                tags=', '.join(entry_dict.get('tags', [])),
                content=entry_dict.get('content', '')
            )
            formatted_parts.append(part)
        
        return {"output": joiner.join(formatted_parts)}