# backend/core/utils.py

from typing import Any, Dict, List

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    所有读取和写入操作都会直接作用于原始的底层字典。
    当访问一个值为字典的属性时，它会自动将该字典也包装成 DotAccessibleDict。
    """
    def __init__(self, data: Dict[str, Any]):
        object.__setattr__(self, "_data", data)

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        """递归包装值。如果值是字典，包装它；如果是列表，递归包装其内容。"""
        if isinstance(value, dict):
            # 如果是字典，返回一个新的代理实例
            return cls(value)
        if isinstance(value, list):
            # 如果是列表，递归处理列表中的每一项
            return [cls._wrap(item) for item in value]
        # 其他类型原样返回
        return value

    def __getattr__(self, name: str) -> Any:
        """当访问 obj.key 时调用。"""
        try:
            # 获取原始值
            value = self._data[name]
            # 在返回值之前，递归地包装它！
            return self._wrap(value)
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        """当执行 obj.key = value 时调用。"""
        self._data[name] = value

    def __delattr__(self, name: str):
        """当执行 del obj.key 时调用。"""
        try:
            del self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    # 保持辅助方法不变
    def __repr__(self) -> str:
        return f"DotAccessibleDict({self._data})"
    
    def __getitem__(self, key):
        return self._wrap(self._data[key])
    
    def __setitem__(self, key, value):
        self._data[key] = value