# plugins/core_engine/runtimes/data_runtimes.py
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

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
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        items = config.get("items")
        template = config.get("template")
        if items is None or template is None:
            raise ValueError("FormatRuntime requires 'items' and 'template' in its config.")
        
        formatted_parts = []
        if isinstance(items, list):
            joiner = config.get("joiner", "\n")
            for item in items:
                try:
                    # 支持 item 是字典的情况 (e.g., template="{item[name]}")
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
            # 对于字典，通常没有 joiner 的概念，但为了一致性，我们也允许它
            joiner = config.get("joiner", "\n")
            return {"output": joiner.join(formatted_parts)}
            
        else:
            raise TypeError(f"FormatRuntime 'items' field must be a list or a dict, not {type(items).__name__}.")

class ParseRuntime(RuntimeInterface):
    """
    system.data.parse: 将字符串（如LLM的输出）解析为结构化的数据对象。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        text = config.get("text")
        fmt = config.get("format")
        strict = config.get("strict", False)

        if text is None or fmt is None:
            raise ValueError("ParseRuntime requires 'text' and 'format' in its config.")
        
        try:
            if fmt == "json":
                return {"output": json.loads(text)}
            
            elif fmt == "xml":
                root = ET.fromstring(text)
                selector = config.get("selector")
                if selector:
                    # 简化版 XPath, 只支持标签名
                    found_element = root.find(selector.strip('/'))
                    if found_element is not None:
                        return {"output": found_element.text}
                    else:
                        return {"output": None}
                else:
                    return {"output": etree_to_dict(root)}
            
            else:
                raise ValueError(f"Unsupported format '{fmt}'. Supported formats are 'json', 'xml'.")

        except Exception as e:
            if strict:
                raise e
            return {"output": {"error": str(e), "original_text": text}}

class RegexRuntime(RuntimeInterface):
    """
    system.data.regex: 对输入文本执行正则表达式匹配，并提取匹配内容。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        text = str(config.get("text", ""))
        pattern = config.get("pattern")
        mode = config.get("mode", "search")

        if not pattern:
            raise ValueError("RegexRuntime requires a 'pattern' in its config.")
        
        if mode == "search":
            match = re.search(pattern, text)
            if not match:
                return {"output": None}
            if match.groupdict():
                return {"output": match.groupdict()}
            return {"output": match.group(0)}
        
        elif mode == "find_all":
            matches = re.findall(pattern, text)
            return {"output": matches}
        
        else:
            raise ValueError(f"Invalid mode '{mode}'. Supported modes are 'search', 'find_all'.")