# plugins/core_llm/runtime.py

import logging
from datetime import datetime
from typing import Dict, Any, List, Literal, Union, Type, Optional
from pydantic import BaseModel, Field, field_validator

from plugins.core_engine.contracts import ExecutionContext, RuntimeInterface, MacroEvaluationServiceInterface
from .contracts import LLMResponse, LLMRequestFailedError

logger = logging.getLogger(__name__)

class LLMRuntime(RuntimeInterface):
    """
    一个强大的运行时，它通过"列表展开"机制编排一个结构化的消息列表，
    然后通过 Hevno LLM Gateway 发起调用。
    """
    
    class MessagePart(BaseModel):
        type: Literal["MESSAGE_PART"] = "MESSAGE_PART"
        role: str = Field(..., description="消息的角色 (例如 'system', 'user', 'model').")
        content: Any = Field(..., description="消息的内容，支持宏。")
        is_enabled: Any = Field(default=True, description="一个布尔值或宏，用于条件性地包含此部分。")

    class InjectMessages(BaseModel):
        type: Literal["INJECT_MESSAGES"] = "INJECT_MESSAGES"
        source: Any = Field(..., description="一个宏，其求值结果必须是一个消息列表 (例如来自 memoria.query 的输出)。")
        is_enabled: Any = Field(default=True, description="一个布尔值或宏，用于条件性地包含此部分。")

    class ConfigModel(BaseModel):
        model: str = Field(..., description="要使用的模型名称，格式为 'provider/model_id' (例如, 'gemini/gemini-1.5-pro')。")
        contents: List[Union["LLMRuntime.MessagePart", "LLMRuntime.InjectMessages"]] = Field(
            ..., 
            description="一个定义消息结构的列表，支持静态部分和动态注入。"
        )
        temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="控制生成文本的随机性。")
        max_tokens: Optional[int] = Field(default=None, gt=0, description="限制生成的最大 token 数量。")
        top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="控制 nucleus sampling。")
        top_k: Optional[int] = Field(default=None, gt=0, description="控制 top-k sampling。")

        @field_validator('contents')
        def check_contents_not_empty(cls, v):
            if not v:
                raise ValueError("'contents' list cannot be empty.")
            return v
            
    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
        except Exception as e:
            return {"error": f"Invalid configuration for llm.default: {e}"}

        macro_service: MacroEvaluationServiceInterface = context.shared.services.macro_evaluation_service
        lock = context.shared.global_write_lock
        
        final_messages: List[Dict[str, Any]] = []
        for item_model in validated_config.contents:
            eval_context = macro_service.build_context(context)
            if not await macro_service.evaluate(item_model.is_enabled, eval_context, lock):
                continue
                
            if isinstance(item_model, self.MessagePart):
                evaluated_content = await macro_service.evaluate(item_model.content, eval_context, lock)
                final_messages.append({"role": item_model.role, "content": str(evaluated_content)})

            elif isinstance(item_model, self.InjectMessages):
                injected_messages = await macro_service.evaluate(item_model.source, eval_context, lock)
                if isinstance(injected_messages, list):
                    for msg in injected_messages:
                        if msg and "role" in msg and "content" in msg:
                            final_messages.append({"role": msg["role"], "content": msg["content"]})
                        else:
                            logger.warning(f"Skipping invalid item in injected message list: {msg}")
                elif injected_messages is not None:
                     logger.warning(f"Macro for INJECT_MESSAGES 'source' did not evaluate to a list. Got {type(injected_messages).__name__}. Ignoring.")

        # 从验证过的配置中提取参数
        llm_params = validated_config.model_dump(exclude={"model", "contents", "prompt"}, exclude_none=True)
        llm_service = context.shared.services.llm_service
        node = kwargs.get("node")
        
        request_payload = {
            "model_name": validated_config.model,
            "messages": final_messages,
            **llm_params
        }
        
        response: LLMResponse = None
        try:
            response = await llm_service.request(**request_payload)
            
            if "diagnostics_log" in context.run_vars:
                diagnostic_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "node_id": node.id if node else 'unknown',
                    "runtime": "llm.default",
                    "request": request_payload,
                    "response": response.model_dump(mode='json') if response else None 
                }
                context.run_vars["diagnostics_log"].append(diagnostic_entry)

            if response.error_details:
                return {"error": response.error_details.message, "error_type": response.error_details.error_type.value, "details": response.error_details.model_dump()}
            return {"output": response.content, "usage": response.usage, "model_name": response.model_name}
        
        except LLMRequestFailedError as e:
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