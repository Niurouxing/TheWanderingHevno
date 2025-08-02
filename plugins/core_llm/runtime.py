# plugins/core_llm/runtime.py

import asyncio 
from typing import Dict, Any, Optional
from backend.core.interfaces import RuntimeInterface
from backend.core.registry import runtime_registry 
from backend.core.state import ExecutionContext
from backend.llm.models import LLMResponse, LLMRequestFailedError



@runtime_registry.register("llm.default")
class LLMRuntime(RuntimeInterface):
    """
    一个轻量级的运行时，它通过 Hevno LLM Gateway 发起 LLM 调用。
    它的职责是：
    1. 从 config 中解析出调用意图（模型、prompt 等）。
    2. 从上下文中获取 LLMService。
    3. 调用 LLMService.request()。
    4. 将结果（成功或失败）格式化为标准的节点输出。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        # ... (解析 config 的逻辑不变) ...
        model_name = config.get("model")
        prompt = config.get("prompt")
        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        if not model_name:
            raise ValueError("LLMRuntime requires a 'model' field in its config (e.g., 'gemini/gemini-1.5-flash').")
        if not prompt:
            raise ValueError("LLMRuntime requires a 'prompt' field in its config.")

        # 所有非'model'和'prompt'的键都作为额外参数传递
        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt"]}

        # 2. 从共享上下文中获取 LLM Service
        llm_service = context.shared.services.llm

        try:
            # 3. 调用 Gateway
            response: LLMResponse = await llm_service.request(
                model_name=model_name,
                prompt=prompt,
                **llm_params
            )
            
            # 4. 处理成功或过滤的响应
            if response.error_details:
                # 这是一个“软失败”，比如内容过滤
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
            # 5. 处理硬失败（所有重试都用尽后）
            print(f"ERROR: LLM request failed for node after all retries. Error: {e}")
            return {
                "error": str(e),
                "details": e.last_error.model_dump() if e.last_error else None
            }
