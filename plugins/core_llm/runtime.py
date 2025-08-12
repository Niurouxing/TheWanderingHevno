# plugins/core_llm/runtime.py

import logging
from datetime import datetime
from typing import Dict, Any, List

from plugins.core_engine.contracts import ExecutionContext, RuntimeInterface, MacroEvaluationServiceInterface
from .contracts import LLMResponse, LLMRequestFailedError

logger = logging.getLogger(__name__)

class LLMRuntime(RuntimeInterface):
    """
    一个强大的运行时，它通过“列表展开”机制编排一个结构化的消息列表，
    然后通过 Hevno LLM Gateway 发起调用。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        model_name = config.get("model")
        if not model_name:
            raise ValueError("LLMRuntime requires a 'model' field in its config (e.g., 'gemini/gemini-2.5-flash').")

        if "prompt" in config:
            logger.warning("The 'prompt' field in 'llm.default' is deprecated and will be ignored. Please use the 'contents' list instead.")
        
        contents_config = config.get("contents")
        if not isinstance(contents_config, list):
            raise ValueError("LLMRuntime requires a 'contents' field in its config, which must be a list of message parts or injection directives.")
            
        macro_service: MacroEvaluationServiceInterface = context.shared.services.macro_evaluation_service
        lock = context.shared.global_write_lock
        
        final_messages: List[Dict[str, Any]] = []
        for item in contents_config:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid item in 'contents' list: {item}. Must be a dictionary.")
                continue

            is_enabled_macro = item.get("is_enabled", True)
            eval_context = macro_service.build_context(context)
            if not await macro_service.evaluate(is_enabled_macro, eval_context, lock):
                continue
                
            item_type = item.get("type", "MESSAGE_PART")

            if item_type == "MESSAGE_PART":
                role = item.get("role")
                content_macro = item.get("content")
                if not role or content_macro is None:
                    logger.warning(f"Skipping MESSAGE_PART with missing 'role' or 'content': {item}")
                    continue
                
                evaluated_content = await macro_service.evaluate(content_macro, eval_context, lock)
                final_messages.append({"role": role, "content": str(evaluated_content)})

            elif item_type == "INJECT_MESSAGES":
                source_macro = item.get("source")
                if not source_macro:
                    logger.warning(f"Skipping INJECT_MESSAGES with missing 'source': {item}")
                    continue
                
                injected_messages = await macro_service.evaluate(source_macro, eval_context, lock)
                
                if isinstance(injected_messages, list):
                    for msg in injected_messages:
                        # --- FIX: Loosen validation and convert to plain dict ---
                        if msg and "role" in msg and "content" in msg:
                            # Append a new plain dict to ensure compatibility
                            final_messages.append({"role": msg["role"], "content": msg["content"]})
                        else:
                            logger.warning(f"Skipping invalid item in injected message list: {msg}")
                elif injected_messages is not None:
                     logger.warning(f"Macro for INJECT_MESSAGES 'source' did not evaluate to a list. Got {type(injected_messages).__name__}. Ignoring.")
            
            else:
                logger.warning(f"Unknown item type '{item_type}' in 'contents' list. Skipping.")

        llm_params = {k: v for k, v in config.items() if k not in ["model", "prompt", "contents"]}
        llm_service = context.shared.services.llm_service

        node = kwargs.get("node")
        
        # 准备要发送的请求体
        request_payload = {
            "model_name": model_name,
            "messages": final_messages,
            **llm_params
        }
        
        response: LLMResponse = None
        try:
            response = await llm_service.request(**request_payload)
            
            # --- 无论成功与否，都记录日志 ---
            if "diagnostics_log" in context.run_vars:
                diagnostic_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "node_id": node.id if node else 'unknown',
                    "runtime": "llm.default",
                    "request": request_payload,
                    # 使用 model_dump 确保 Pydantic 模型被正确序列化
                    "response": response.model_dump(mode='json') if response else None 
                }
                context.run_vars["diagnostics_log"].append(diagnostic_entry)

            if response.error_details:
                return {"error": response.error_details.message, "error_type": response.error_details.error_type.value, "details": response.error_details.model_dump()}
            return {"llm_output": response.content, "usage": response.usage, "model_name": response.model_name}
        
        except LLMRequestFailedError as e:
            # --- 在异常情况下也记录日志 ---
            if "diagnostics_log" in context.run_vars:
                diagnostic_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "node_id": node.id if node else 'unknown',
                    "runtime": "llm.default",
                    "request": request_payload,
                    "response": {
                        "status": "ERROR",
                        "error_details": {
                            "message": str(e),
                            "last_known_provider_error": e.last_error.model_dump(mode='json') if e.last_error else None
                        }
                    }
                }
                context.run_vars["diagnostics_log"].append(diagnostic_entry)
            
            return {"error": str(e), "details": e.last_error.model_dump() if e.last_error else None}