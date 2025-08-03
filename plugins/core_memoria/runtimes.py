# plugins/core_memoria/runtimes.py

import logging
from typing import Dict, Any, List

from backend.core.contracts import BackgroundTaskManager 
from plugins.core_engine.contracts import ExecutionContext

from plugins.core_engine.contracts import RuntimeInterface
from .models import Memoria, MemoryEntry
from .tasks import run_synthesis_task

logger = logging.getLogger(__name__)


class MemoriaAddRuntime(RuntimeInterface):
    """
    向指定的记忆流中添加一条新的记忆条目。
    如果满足条件，会自动触发一个后台任务来执行记忆综合。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        stream_name = config.get("stream")
        content = config.get("content")
        if not stream_name or not content:
            raise ValueError("MemoriaAddRuntime requires 'stream' and 'content' in its config.")
        
        level = config.get("level", "event")
        tags = config.get("tags", [])
        
        memoria_data = context.shared.world_state.setdefault("memoria", {"__global_sequence__": 0})
        memoria = Memoria.model_validate(memoria_data)
        
        # 获取或创建流
        stream = memoria.get_stream(stream_name)
        if stream is None:
            from .models import MemoryStream
            stream = MemoryStream()

        # 创建新条目
        new_entry = MemoryEntry(
            sequence_id=memoria.get_next_sequence_id(),
            level=level,
            tags=tags,
            content=str(content)
        )
        stream.entries.append(new_entry)
        
        # 【修复】使用新的公共字段名
        stream.synthesis_trigger_counter += 1
        
        # 将更新后的流写回
        memoria.set_stream(stream_name, stream)
        context.shared.world_state["memoria"] = memoria.model_dump()
        
        # 检查是否需要触发后台综合任务
        synth_config = stream.config.auto_synthesis
        # 【修复】使用新的公共字段名
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
            memoria.set_stream(stream_name, stream)
            context.shared.world_state["memoria"] = memoria.model_dump()

        return {"output": new_entry.model_dump()}


class MemoriaQueryRuntime(RuntimeInterface):
    """
    根据声明式条件从一个记忆流中检索条目。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        stream_name = config.get("stream")
        if not stream_name:
            raise ValueError("MemoriaQueryRuntime requires a 'stream' name in its config.")

        memoria_data = context.shared.world_state.get("memoria", {})
        memoria = Memoria.model_validate(memoria_data)
        stream = memoria.get_stream(stream_name)
        
        if not stream:
            return {"output": []} # 如果流不存在，返回空列表

        # --- 过滤逻辑 ---
        results = stream.entries
        
        # 按 levels 过滤
        levels_to_get = config.get("levels")
        if isinstance(levels_to_get, list):
            results = [entry for entry in results if entry.level in levels_to_get]

        # 按 tags 过滤
        tags_to_get = config.get("tags")
        if isinstance(tags_to_get, list):
            tags_set = set(tags_to_get)
            results = [entry for entry in results if tags_set.intersection(entry.tags)]

        # 获取最新的 N 条
        latest_n = config.get("latest")
        if isinstance(latest_n, int):
            # 先按 sequence_id 排序确保顺序正确
            results.sort(key=lambda e: e.sequence_id)
            results = results[-latest_n:]
            
        # 按顺序返回
        order = config.get("order", "ascending")
        reverse = (order == "descending")
        results.sort(key=lambda e: e.sequence_id, reverse=reverse)

        return {"output": [entry.model_dump() for entry in results]}


class MemoriaAggregateRuntime(RuntimeInterface):
    """
    将一批记忆条目（通常来自 query 的输出）聚合成一段格式化的文本。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
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