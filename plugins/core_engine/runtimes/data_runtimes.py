# plugins/core_engine/runtimes/data_runtimes.py
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Union, Literal, Type, Optional
from pydantic import BaseModel, Field

from ..contracts import ExecutionContext, RuntimeInterface

# --- XML to Dict Helper ---
def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = {}
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {t.tag: dd}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

class FormatRuntime(RuntimeInterface):
    """
    system.data.format: 将列表或字典数据源格式化为单一字符串。
    """
    class ConfigModel(BaseModel):
        items: Union[List[Any], Dict[str, Any]] = Field(..., description="要格式化的数据源，可以是一个列表或字典。")
        template: str = Field(..., description="格式化模板。对于列表，使用 {item}；对于字典，使用 {key} 和 {value}。")
        joiner: str = Field(default="\n", description="用于连接每个格式化部分的字符串。")

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            items = validated_config.items
            template = validated_config.template
            joiner = validated_config.joiner

            formatted_parts = []
            if isinstance(items, list):
                for item in items:
                    try:
                        if isinstance(item, dict):
                             formatted_parts.append(template.format(item=item, **item))
                        else:
                             formatted_parts.append(template.format(item=item))
                    except (KeyError, IndexError, TypeError) as e:
                        raise ValueError(f"Error formatting item with template: {e}. Item: {item}, Template: '{template}'")
                return {"output": joiner.join(formatted_parts)}
            
            elif isinstance(items, dict):
                for key, value in items.items():
                    formatted_parts.append(template.format(key=key, value=value))
                return {"output": joiner.join(formatted_parts)}

            # This part should not be reached due to Pydantic validation
            return {"output": ""}

        except Exception as e:
            return {"error": f"Invalid configuration or execution error in system.data.format: {e}"}

class ParseRuntime(RuntimeInterface):
    """
    system.data.parse: 将字符串（如LLM的输出）解析为结构化的数据对象。
    """
    class ConfigModel(BaseModel):
        text: str = Field(..., description="待解析的输入字符串。")
        format: Literal["json", "xml"] = Field(..., description="要使用的解析格式。")
        selector: Optional[str] = Field(default=None, description="仅当格式为 'xml' 时使用，一个简化的类XPath选择器，用于提取特定元素。")
        strict: bool = Field(default=False, description="是否启用严格模式。如果为 true，解析失败将导致节点错误；否则，将返回一个包含错误信息的对象。")

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            text = validated_config.text
            fmt = validated_config.format
            strict = validated_config.strict

            if fmt == "json":
                return {"output": json.loads(text)}
            
            elif fmt == "xml":
                root = ET.fromstring(text)
                selector = validated_config.selector
                if selector:
                    found_element = root.find(selector.strip('/'))
                    return {"output": found_element.text if found_element is not None else None}
                else:
                    return {"output": etree_to_dict(root)}

        except Exception as e:
            if config.get("strict", False): # Use original config for strict check before validation
                raise e
            return {"output": {"error": str(e), "original_text": config.get("text")}}
        
        # Should not be reached
        return {}


class RegexRuntime(RuntimeInterface):
    """
    system.data.regex: 对输入文本执行正则表达式匹配，并提取匹配内容。
    """
    class ConfigModel(BaseModel):
        text: str = Field(..., description="要进行匹配的源文本。")
        pattern: str = Field(..., description="正则表达式模式。支持命名捕获组 `(?P<name>...)`。")
        mode: Literal["search", "find_all"] = Field(default="search", description="匹配模式。'search' 返回第一个匹配项，'find_all' 返回所有匹配项的列表。")

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            text = validated_config.text
            pattern = validated_config.pattern
            mode = validated_config.mode
            
            if mode == "search":
                match = re.search(pattern, text)
                if not match:
                    return {"output": None}
                return {"output": match.groupdict() or match.group(0)}
            
            elif mode == "find_all":
                return {"output": re.findall(pattern, text)}

        except Exception as e:
             return {"error": f"Invalid configuration or execution error in system.data.regex: {e}"}

        return {}