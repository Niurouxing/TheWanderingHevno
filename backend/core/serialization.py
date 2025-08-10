# backend/core/serialization.py

# 【核心修改】导入 cloudpickle 而不是 pickle
import cloudpickle
import base64
import json
from typing import Any

def pickle_fallback_encoder(obj: Any) -> Any:
    """
    一个专门用作 Pydantic `model_dump` fallback 的编码器。
    当 Pydantic 遇到无法序列化的对象时，此函数会被调用。
    """
    try:
        pickled_bytes = cloudpickle.dumps(obj)
        b64_string = base64.b64encode(pickled_bytes).decode('ascii')
        return {
            "__hevno_pickle__": True,
            "data": b64_string
        }
    except Exception as e:
        # Pydantic 的 fallback 机制期望在失败时能得到一个可序列化的错误表示
        # 或者直接抛出错误。这里我们选择抛出，让调用者知道问题。
        raise TypeError(f"Object of type {type(obj).__name__} could not be pickled by cloudpickle: {e}") from e

def custom_json_decoder_object_hook(obj: dict) -> Any:
    """
    这个解码器保持不变，因为它需要处理 `__hevno_pickle__` 结构。
    """
    if "__hevno_pickle__" in obj:
        b64_string = obj['data']
        pickled_bytes = base64.b64decode(b64_string)
        try:
            return cloudpickle.loads(pickled_bytes)
        except Exception as e:
            return {"__unpickling_error__": f"Failed to unpickle object with cloudpickle: {e}"}
    return obj