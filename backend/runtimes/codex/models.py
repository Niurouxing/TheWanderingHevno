# backend/runtimes/codex/models.py
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator

class TriggerMode(str, Enum):
    ALWAYS_ON = "always_on"
    ON_KEYWORD = "on_keyword"

class CodexEntry(BaseModel):
    """定义单个知识条目的结构。"""
    id: str
    content: str  # [Macro]
    is_enabled: Any = Field(default=True)  # [Macro] bool or str
    trigger_mode: TriggerMode = Field(default=TriggerMode.ALWAYS_ON)
    keywords: Any = Field(default_factory=list)  # [Macro] List[str] or str
    priority: Any = Field(default=0)  # [Macro] int or str
    
    model_config = ConfigDict(extra='forbid') # 确保没有多余字段

class CodexConfig(BaseModel):
    """定义单个法典级别的配置。"""
    recursion_depth: int = Field(default=3, ge=0, description="此法典参与递归时的最大深度。")
    
    model_config = ConfigDict(extra='forbid')

class Codex(BaseModel):
    """定义一个完整的法典。"""
    description: Optional[str] = None
    config: CodexConfig = Field(default_factory=CodexConfig)
    entries: List[CodexEntry]
    metadata: Dict[str, Any] = Field(default_factory=dict) 

    model_config = ConfigDict(extra='forbid')

class CodexCollection(RootModel[Dict[str, Codex]]):
    """
    代表 world.codices 的顶层结构。
    模型本身是一个 `Dict[str, Codex]`。
    """
    pass

# 用于运行时内部处理的数据结构
class ActivatedEntry(BaseModel):
    entry_model: CodexEntry
    codex_name: str
    codex_config: CodexConfig
    
    # 结构性宏求值后的结果
    priority_val: int
    keywords_val: List[str]
    is_enabled_val: bool
    
    # 触发信息
    source_text: str
    matched_keywords: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)