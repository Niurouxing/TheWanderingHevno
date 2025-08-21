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
        max_output_tokens: Optional[int] = Field(default=None, gt=0, description="限制生成的最大 token 数量。")
        top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="控制 nucleus sampling。")
        top_k: Optional[int] = Field(default=None, gt=0, description="控制 top-k sampling。")
        
        # 这个布尔字段会自动被前端渲染为开关 (Switch)
        include_thoughts: Optional[bool] = Field(
            default=None,
            title="启用思考链",
            description="如果为 true，模型将在最终回答前输出其思考过程。仅部分模型支持。"
        )
        # 这个整数/数字字段会自动被渲染为数字输入框
        thinking_budget: Optional[int] = Field(
            default=None,
            gt=0,
            title="思考预算",
            description="为思考过程分配的最大 token 数量。仅在启用思考链时有效。"
        )

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

        # --- [核心优化] 从扁平化的配置中重新构建 provider 期望的参数结构 ---
        llm_params = validated_config.model_dump(
            # 排除我们手动处理的字段
            exclude={"model", "contents", "include_thoughts", "thinking_budget"}, 
            # 排除值为 None 的字段，保持请求体干净
            exclude_none=True
        )
        
        # 如果用户配置了任何一个思考链相关的参数，则构建 thinking_config 字典
        thinking_config = {}
        if validated_config.include_thoughts is not None:
            thinking_config['include_thoughts'] = validated_config.include_thoughts
        if validated_config.thinking_budget is not None:
            thinking_config['thinking_budget'] = validated_config.thinking_budget
        
        # 只有在 thinking_config 不为空时，才将其添加到最终参数中
        if thinking_config:
            llm_params['thinking_config'] = thinking_config

        llm_service = context.shared.services.llm_service
        node = kwargs.get("node")
        
        request_payload = {
            "model_name": validated_config.model,
            "messages": final_messages,
            **llm_params
        }
        
        response: LLMResponse = None
    
        moment_state = context.shared.moment_state
        if '_log_info' not in moment_state or not isinstance(moment_state.get('_log_info'), list):
            moment_state['_log_info'] = []
            
        try:
            response = await llm_service.request(**request_payload)
            
            # --- [核心修改] ---
            # 优先使用从 response 中回传的、最准确的请求数据来记录日志。
            # 如果 response 中没有（为了兼容旧的 provider），则回退到我们最初构建的 payload。
            log_request_data = response.final_request_payload if response and response.final_request_payload else request_payload

            diagnostic_entry = {
                "type": "llm_call",
                "timestamp": datetime.now().isoformat(),
                "node_id": node.id if node else 'unknown',
                "data": {
                    "request": log_request_data, # <-- 使用最准确的数据
                    "response": response.model_dump(mode='json') if response else None 
                }
            }
            moment_state['_log_info'].append(diagnostic_entry)

            if response.error_details:
                return {"error": response.error_details.message, "error_type": response.error_details.error_type.value, "details": response.error_details.model_dump()}
            return {"output": response.content, "usage": response.usage, "model_name": response.model_name}
        
        except LLMRequestFailedError as e:
            # 在硬性失败的情况下，我们没有 response 对象，只能记录原始的 request_payload。
            diagnostic_entry = {
                "type": "llm_call",
                "timestamp": datetime.now().isoformat(),
                "node_id": node.id if node else 'unknown',
                "data": {
                    "request": request_payload, # <-- 在此场景下，这是我们能获取到的最准确信息
                    "response": {
                        "status": "ERROR",
                        "error_details": {
                            "message": str(e),
                            "last_known_provider_error": e.last_error.model_dump(mode='json') if e.last_error else None
                        }
                    }
                }
            }
            moment_state['_log_info'].append(diagnostic_entry)
            
            return {"error": str(e), "details": e.last_error.model_dump() if e.last_error else None}