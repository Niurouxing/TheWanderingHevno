# plugins/core_memoria/models.py
from __future__ import annotations
import logging
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, RootModel, ConfigDict

logger = logging.getLogger(__name__)

# --- Core Data Models for Memoria Structure ---

class MemoryEntry(BaseModel):
    """一个单独的、结构化的记忆条目。"""
    id: UUID = Field(default_factory=uuid4)
    sequence_id: int = Field(..., description="在所有流中唯一的、单调递增的因果序列号。")
    level: str = Field(default="event", description="记忆的层级，如 'event', 'summary', 'milestone'。")
    tags: List[str] = Field(default_factory=list, description="用于快速过滤和检索的标签。")
    content: str = Field(..., description="记忆条目的文本内容。")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutoSynthesisConfig(BaseModel):
    """自动综合（大总结）的行为配置。"""
    enabled: bool = Field(default=False)
    trigger_count: int = Field(default=10, gt=0, description="触发综合所需的条目数量。")
    level: str = Field(default="summary", description="综合后产生的新条目的层级。")
    model: str = Field(default="gemini/gemini-1.5-flash", description="用于执行综合的 LLM 模型。")
    prompt: str = Field(
        default="The following is a series of events. Please provide a concise summary.\n\nEvents:\n{events_text}",
        description="用于综合的 LLM 提示模板。必须包含 '{events_text}' 占位符。"
    )


class MemoryStreamConfig(BaseModel):
    """每个记忆流的独立配置。"""
    auto_synthesis: AutoSynthesisConfig = Field(default_factory=AutoSynthesisConfig)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryStream(BaseModel):
    """一个独立的记忆回廊，包含它自己的配置和条目列表。"""
    config: MemoryStreamConfig = Field(default_factory=MemoryStreamConfig)
    entries: List[MemoryEntry] = Field(default_factory=list)
    
    synthesis_trigger_counter: int = Field(
        default=0, 
        description="Internal counter for auto-synthesis trigger. This is part of the persisted state."
    )
class Memoria(RootModel[Dict[str, Any]]):
    """
    代表 world.memoria 的顶层结构。
    它是一个字典，键是流名称，值是 MemoryStream 对象。
    还包含一个全局序列号，以确保因果关系的唯一性。
    """
    root: Dict[str, Any] = Field(default_factory=lambda: {"__global_sequence__": 0})
    
    def get_stream(self, stream_name: str) -> Optional[MemoryStream]:
        """安全地获取一个 MemoryStream 的 Pydantic 模型实例。"""
        stream_data = self.root.get(stream_name)
        if isinstance(stream_data, dict):
            return MemoryStream.model_validate(stream_data)
        return None

    def set_stream(self, stream_name: str, stream_model: MemoryStream):
        """将一个 MemoryStream 模型实例写回到根字典中。"""
        self.root[stream_name] = stream_model.model_dump()

    def get_next_sequence_id(self) -> int:
        """获取并递增全局序列号，确保原子性。"""
        current_seq = self.root.get("__global_sequence__", 0)
        next_seq = current_seq + 1
        self.root["__global_sequence__"] = next_seq
        return next_seq