# backend/core/utils.py

from typing import Any, Dict

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    【关键修正】所有读取和写入操作都会直接作用于原始的底层字典。
    """
    def __init__(self, data: Dict[str, Any]):
        # 不再使用 object.__setattr__，而是直接存储引用。
        # Pydantic的BaseModel等复杂对象可能需要它，但我们这里用于简单字典，
        # 直接存储引用更清晰。
        self._data = data

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        """递归包装值。如果值是字典，包装它；如果是列表，递归包装其内容。"""
        if isinstance(value, dict):
            return cls(value)
        if isinstance(value, list):
            # 列表本身不被包装，但其内容需要递归检查
            return [cls._wrap(item) for item in value]
        return value

    def __getattr__(self, name: str) -> Any:
        """当访问 obj.key 时调用。"""
        try:
            value = self._data[name]
            return self._wrap(value)
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        """当执行 obj.key = value 时调用。"""
        # --- 核心修正 ---
        # 如果 name 是 `_data`，就设置实例属性，否则直接修改底层字典。
        if name == '_data':
            super().__setattr__(name, value)
        else:
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