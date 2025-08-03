# plugins/core_codex/models.py
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, RootModel, ConfigDict, field_validator

class TriggerMode(str, Enum):
    ALWAYS_ON = "always_on"
    ON_KEYWORD = "on_keyword"

class CodexEntry(BaseModel):
    id: str
    content: str
    is_enabled: Any = Field(default=True)
    trigger_mode: TriggerMode = Field(default=TriggerMode.ALWAYS_ON)
    keywords: Any = Field(default_factory=list)
    priority: Any = Field(default=0)
    model_config = ConfigDict(extra='forbid')

class CodexConfig(BaseModel):
    recursion_depth: int = Field(default=3, ge=0)
    model_config = ConfigDict(extra='forbid')

class Codex(BaseModel):
    description: Optional[str] = None
    config: CodexConfig = Field(default_factory=CodexConfig)
    entries: List[CodexEntry]
    metadata: Dict[str, Any] = Field(default_factory=dict) 
    model_config = ConfigDict(extra='forbid')

class CodexCollection(RootModel[Dict[str, Codex]]):
    pass

# 用于运行时内部处理的数据结构
class ActivatedEntry(BaseModel):
    entry_model: CodexEntry
    codex_name: str
    codex_config: CodexConfig
    
    priority_val: int
    keywords_val: List[str]
    is_enabled_val: bool
    
    source_text: str
    matched_keywords: List[str] = Field(default_factory=list)
    
    # 【确认此字段存在】
    depth: int = Field(default=0)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)