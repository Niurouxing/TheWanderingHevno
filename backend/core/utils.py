# backend/core/utils.py

from typing import Any, Dict, List
from pathlib import Path

def unwrap_dot_accessible_dicts(data: Any) -> Any:
    """
    递归地将 DotAccessibleDict 实例转换回普通的 Python 字典。
    这对于将包含这些对象的数据结构序列化为 JSON 至关重要。
    """
    if isinstance(data, DotAccessibleDict):
        # 基础情况：解包 DotAccessibleDict 并对其内容进行递归调用
        return unwrap_dot_accessible_dicts(data._data)
    elif isinstance(data, dict):
        # 递归情况：遍历字典的值
        return {key: unwrap_dot_accessible_dicts(value) for key, value in data.items()}
    elif isinstance(data, list):
        # 递归情况：遍历列表的项
        return [unwrap_dot_accessible_dicts(item) for item in data]
    else:
        # 基本类型：直接返回
        return data

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    所有读取和写入操作都会直接作用于原始的底层字典。
    """
    def __init__(self, data: Dict[str, Any]):
        # 使用 object.__setattr__ 来避免触发我们自己的 __setattr__
        object.__setattr__(self, '_data', data)

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        if isinstance(value, dict):
            # 避免重复包装
            if not isinstance(value, cls):
                return cls(value)
            return value
        if isinstance(value, list):
            return [cls._wrap(item) for item in value]
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getattr__(self, name: str) -> Any:
        if name.startswith('__'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            
        try:
            value = self._data[name]
            return self._wrap(value)
        except KeyError:
            # 允许调用底层字典的方法，如 .keys(), .items()
            underlying_attr = getattr(self._data, name, None)
            if callable(underlying_attr):
                return underlying_attr
            raise AttributeError(f"'{type(self).__name__}' object has no attribute or method '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name == '_data':
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __delattr__(self, name: str):
        try:
            del self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __repr__(self) -> str:
        return f"DotAccessibleDict({self._data})"
    
    def __getitem__(self, key):
        return self._wrap(self._data[key])
    
    def __setitem__(self, key, value):
        self._data[key] = value