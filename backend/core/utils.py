# backend/core/utils.py

from typing import Any, Dict, List, Tuple, Union
from pathlib import Path

def _navigate_to_sub_path(
    root_obj: Dict[str, Any], 
    sub_path: str, 
    create_if_missing: bool = False
) -> Tuple[Union[Dict, List], Union[str, int]]:
    """
    Navigates a nested structure and returns the PARENT object and the FINAL key/index.
    
    Example: for path "a/b/0", it returns the list at root['a']['b'] and the index 0.
    This allows the caller to perform GET, SET, or DELETE operations.
    
    Args:
        root_obj: The dictionary to start from.
        sub_path: A slash-separated path string (e.g., "data/users/0/name").
        create_if_missing: If True, creates intermediate dictionaries for PUT operations.
        
    Returns:
        A tuple of (parent_object, final_key_or_index).
        
    Raises:
        HTTPException if the path is invalid or not found.
    """
    parts = [p for p in sub_path.split('/') if p]
    if not parts:
        raise HTTPException(status_code=400, detail="Sub-path cannot be empty.")

    current_obj = root_obj
    for i, part in enumerate(parts[:-1]): # Iterate to the second-to-last part
        try:
            # Try to convert to int for list access
            try:
                key = int(part)
                current_obj = current_obj[key]
                continue
            except (ValueError, TypeError):
                # It's a dictionary key
                if part not in current_obj:
                    if create_if_missing and isinstance(current_obj, dict):
                        current_obj[part] = {}
                    else:
                        raise HTTPException(status_code=404, detail=f"Path segment '{part}' not found.")
                current_obj = current_obj[part]

        except (KeyError, IndexError, TypeError):
            raise HTTPException(status_code=404, detail=f"Path not found at segment '{part}'.")

    # Now handle the final part
    final_key = parts[-1]
    try: # Try to convert final key to int
        final_key = int(final_key)
    except ValueError:
        pass # It's a string key
        
    return current_obj, final_key

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
    一个递归代理类，它包装一个字典，允许通过点符号进行属性访问。
    此版本确保对嵌套的可变对象（如列表）的修改能够正确地作用于原始数据。
    """
    def __init__(self, data: Dict[str, Any]):
        # 使用 object.__setattr__ 来避免触发我们自己的 __setattr__
        object.__setattr__(self, '_data', data)

    @staticmethod
    def _wrap_if_dict(value: Any) -> Any:
        """
        一个静态辅助方法，仅当值为字典时才进行包装。
        """
        if isinstance(value, dict):
            # 避免对已经是代理的对象进行重复包装
            if isinstance(value, DotAccessibleDict):
                return value
            return DotAccessibleDict(value)
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getattr__(self, name: str) -> Any:
        if name.startswith('__'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
            
        try:
            value = self._data[name]
            # 仅当值是字典时才递归包装。
            # 对于列表、字符串、数字等，直接返回原始对象引用。
            return self._wrap_if_dict(value)
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
            # 直接在底层字典上设置值
            self._data[name] = value

    def __delattr__(self, name: str):
        try:
            del self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __repr__(self) -> str:
        return f"DotAccessibleDict({self._data})"
    
    def __getitem__(self, key):
        value = self._data[key]
        # 确保通过方括号访问也能正确工作
        return self._wrap_if_dict(value)
    
    def __setitem__(self, key, value):
        self._data[key] = value