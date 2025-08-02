# plugins/core_llm/runtime.py

from typing import Dict, Any

from backend.core.contracts import ExecutionContext
from plugins.core_engine.interfaces import RuntimeInterface
from .models import LLMResponse, LLMRequestFailedError

# --- 核心修改: 移除 @runtime_registry 装饰器 ---
class LLMRuntime(RuntimeInterface):
    """
    一个轻量级的运行时，它通过 Hevno LLM Gateway 发起 LLM 调用。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        model_name = config.get("model")
        prompt = config.get("prompt")
        
        if not model_name:
            raise ValueError("LLMRuntime requires a 'model' field in its config (e.g., 'gemini/gemini-1.5-flash').")
        if not prompt:
            raise ValueError("LLMRuntime requires a 'prompt' field in its config.")

        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        llm_service = context.shared.services.llm_service

        try:
            response: LLMResponse = await llm_service.request(
                model_name=model_name,
                prompt=prompt,
                **llm_params
            )
            
            if response.error_details:
                return {
                    "error": response.error_details.message,
                    "error_type": response.error_details.error_type.value,
                    "details": response.error_details.model_dump()
                }

            return {
                "llm_output": response.content,
                "usage": response.usage,
                "model_name": response.model_name
            }

        except LLMRequestFailedError as e:
            return {
                "error": str(e),
                "details": e.last_error.model_dump() if e.last_error else None
            }