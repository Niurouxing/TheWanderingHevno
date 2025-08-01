# backend/runtimes/codex/models.py
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel

class TriggerMode(str, Enum):
    ALWAYS_ON = "always_on"
    ON_KEYWORD = "on_keyword"

class CodexEntry(BaseModel):
    """定义单个知识条目的结构。"""
    id: str
    content: str  # [Macro]
    is_enabled: Any = Field(default=True) # [Macro] bool or str
    trigger_mode: TriggerMode = Field(default=TriggerMode.ALWAYS_ON)
    keywords: List[str] = Field(default_factory=list) # [Macro]
    priority: Any = Field(default=0) # [Macro] int or str

class CodexConfig(BaseModel):
    """定义单个法典级别的配置。"""
    recursion_depth: int = Field(default=3, description="此法典参与递归时的最大深度。")

class Codex(BaseModel):
    """定义一个完整的法典。"""
    description: Optional[str] = None
    config: CodexConfig = Field(default_factory=CodexConfig)
    entries: List[CodexEntry]

class CodexCollection(RootModel[Dict[str, Codex]]):
    """
    代表 world.codices 的顶层结构。
    模型本身是一个 `Dict[str, Codex]`。
    """
    pass