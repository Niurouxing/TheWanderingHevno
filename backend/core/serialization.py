# backend/core/serialization.py

import pickle
import base64
import json
from typing import Any

def custom_json_encoder_default(obj: Any) -> Any:
    """
    一个自定义的 JSON 编码器默认函数。
    这是在标准 JSONEncoder 失败后的最后手段。
    它使用 pickle 作为“逃生舱口”。
    """
    try:
        # 启动我们的 pickle "逃生舱"
        pickled_bytes = pickle.dumps(obj)
        b64_string = base64.b64encode(pickled_bytes).decode('ascii')
        return {
            "__hevno_pickle__": True,
            "data": b64_string
        }
    except (pickle.PicklingError, TypeError) as e:
        # 如果连 pickle 都失败了，那就真的没办法了
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable and could not be pickled: {e}") from e

def custom_json_decoder_object_hook(obj: dict) -> Any:
    """
    一个自定义的 JSON 解码器 object_hook。
    如果遇到我们的特殊 pickle 结构，就解包它。
    """
    if "__hevno_pickle__" in obj:
        b64_string = obj['data']
        pickled_bytes = base64.b64decode(b64_string)
        try:
            return pickle.loads(pickled_bytes)
        except (pickle.UnpicklingError, TypeError, AttributeError) as e:
            # 在加载 pickle 失败时返回一个错误对象，而不是让整个加载过程崩溃
            return {"__unpickling_error__": f"Failed to unpickle object: {e}"}
    return obj