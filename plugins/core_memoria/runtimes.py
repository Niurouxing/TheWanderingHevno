# plugins/core_memoria/runtimes.py

import logging
from typing import Dict, Any, List, Literal, Type, Optional
from pydantic import BaseModel, Field

from backend.core.contracts import BackgroundTaskManager 
from plugins.core_engine.contracts import ExecutionContext, RuntimeInterface

from .models import Memoria, MemoryEntry
from .tasks import run_synthesis_task

logger = logging.getLogger(__name__)


class MemoriaAddRuntime(RuntimeInterface):
    """
    向指定的记忆流中添加一条新的记忆条目。
    """
    class ConfigModel(BaseModel):
        stream: str = Field(..., description="要添加记忆的流的名称。")
        content: Any = Field(..., description="记忆的内容，支持宏，将被转换为字符串。")
        level: str = Field(default="event", description="该条目的层级。约定：记录对话时，使用 'user' 或 'model'。")
        tags: List[str] = Field(default_factory=list, description="与该条目关联的标签列表。")

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            stream_name = validated_config.stream
            
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
                level=validated_config.level,
                tags=validated_config.tags,
                content=str(validated_config.content)
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

            return {"output": new_entry.model_dump()}
        except Exception as e:
            return {"error": f"Error in memoria.add: {e}"}


class MemoriaQueryRuntime(RuntimeInterface):
    """
    根据声明式条件从一个记忆流中检索条目。
    """
    class ConfigModel(BaseModel):
        stream: str = Field(..., description="要查询的记忆流的名称。")
        latest: Optional[int] = Field(default=None, gt=0, description="仅返回最新的 N 条记忆。")
        levels: Optional[List[str]] = Field(default=None, description="仅返回 level 在此列表中的条目。")
        tags: Optional[List[str]] = Field(default=None, description="返回至少包含一个指定标签的条目。")
        order: Literal["ascending", "descending"] = Field(
            default="ascending", 
            description="返回结果的排序顺序，基于因果序列号。"
        )
        format: Literal["raw_entries", "message_list", "aggregated_message"] = Field(
            default="raw_entries", 
            description="定义输出格式。'message_list' 专为 llm.default 设计，'aggregated_message' 将内容拼接为单个字符串。"
        )

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            # (这里省略了您添加的日志代码，但假设它们都存在)
            validated_config = self.ConfigModel.model_validate(config)
            stream_name = validated_config.stream
            
            memoria_data = context.shared.moment_state.get("memoria", {})
            memoria = Memoria.model_validate(memoria_data)
            stream = memoria.get_stream(stream_name)
            
            if not stream:
                return {"output": []}

            results = stream.entries
            
            # [已修正] 只有在列表为真（非None且非空）时才进行过滤
            if validated_config.levels: 
                results = [entry for entry in results if entry.level in validated_config.levels]

            # [已修正] 只有在列表为真（非None且非空）时才进行过滤
            if validated_config.tags:
                tags_set = set(validated_config.tags)
                results = [entry for entry in results if tags_set.intersection(entry.tags)]

            if validated_config.latest is not None:
                results.sort(key=lambda e: e.sequence_id)
                results = results[-validated_config.latest:]
                
            reverse = (validated_config.order == "descending")
            results.sort(key=lambda e: e.sequence_id, reverse=reverse)

            # --- [核心修改] 处理返回格式 ---
            if validated_config.format == "message_list":
                message_list = [
                    {"role": entry.level, "content": entry.content}
                    for entry in results if entry.level in ["user", "model"]
                ]
                return {"output": message_list}
            
            # --- [新增] 实现 aggregated_message 模式 ---
            elif validated_config.format == "aggregated_message":
                # 提取所有过滤后条目的 content 字段
                content_list = [entry.content for entry in results]
                # 使用双换行符将它们拼接成一个字符串，这通常能更好地分隔不同的思想或事件
                aggregated_text = "\n\n".join(content_list)
                return {"output": aggregated_text}

            else: # "raw_entries"
                return {"output": [entry.model_dump() for entry in results]}
        except Exception as e:
            logger.error(f"[MemoriaQuery] Error in memoria.query: {e}", exc_info=True)
            return {"error": f"Error in memoria.query: {e}"}