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

class Codex(RootModel[Dict[str, Any]]):
    """
    Codex 定义，本质上是一个字典。
    它必须包含一个 'entries' 键，其值为一个条目列表。
    """
    @field_validator('root')
    @classmethod
    def check_entries_exist_and_are_valid(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if 'entries' not in v or not isinstance(v['entries'], list):
            raise ValueError("A codex must contain an 'entries' list.")
        
        # 手动验证每个条目
        validated_entries = [CodexEntry.model_validate(entry) for entry in v['entries']]
        v['entries'] = validated_entries
        return v

    @property
    def entries(self) -> List[CodexEntry]:
        """提供便捷的属性访问器。"""
        return self.root['entries']

    @property
    def config(self) -> CodexConfig:
        """提供便捷的属性访问器，并处理默认值。"""
        config_data = self.root.get('config', {})
        return CodexConfig.model_validate(config_data)

    @property
    def description(self) -> Optional[str]:
        return self.root.get('description')

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.root.get('metadata', {})

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