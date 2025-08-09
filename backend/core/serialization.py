# backend/core/serialization.py

# 【核心修改】导入 cloudpickle 而不是 pickle
import cloudpickle
import base64
import json
from typing import Any

def custom_json_encoder_default(obj: Any) -> Any:
    """
    一个自定义的 JSON 编码器默认函数。
    这是在标准 JSONEncoder 失败后的最后手段。
    它使用 cloudpickle 作为终极“逃生舱口”，可以序列化动态定义的类和函数。
    """
    try:
        # 使用 cloudpickle.dumps()
        pickled_bytes = cloudpickle.dumps(obj)
        b64_string = base64.b64encode(pickled_bytes).decode('ascii')
        return {
            # 我们仍然使用 __hevno_pickle__ 这个键名，但其内容现在是 cloudpickle 生成的
            "__hevno_pickle__": True,
            "data": b64_string
        }
    except Exception as e:
        # 如果连 cloudpickle 都失败了，那这个对象确实无法序列化
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable and could not be pickled by cloudpickle: {e}") from e

def custom_json_decoder_object_hook(obj: dict) -> Any:
    """
    一个自定义的 JSON 解码器 object_hook。
    如果遇到我们的特殊 pickle 结构，就用 cloudpickle 解包它。
    """
    if "__hevno_pickle__" in obj:
        b64_string = obj['data']
        pickled_bytes = base64.b64decode(b64_string)
        try:
            # 使用 cloudpickle.loads()
            return cloudpickle.loads(pickled_bytes)
        except Exception as e:
            return {"__unpickling_error__": f"Failed to unpickle object with cloudpickle: {e}"}
    return obj