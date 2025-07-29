# backend/runtimes/base_runtimes.py
from backend.core.runtime import RuntimeInterface, ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点。它只关心自己的配置值。"""
    async def execute(self, step_input: Dict[str, Any], pipeline_state: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 这个简单的 Runtime 只需要 step_input (即它自己的配置)
        return {"output": step_input.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """通用的模板渲染运行时。"""
    async def execute(self, step_input: Dict[str, Any], pipeline_state: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 它可能需要 step_input 中的模板字符串
        template_str = step_input.get("template", "")
        if not template_str:
            # 如果在上一步的输出中找不到，它可以回退到整个流水线的状态中去寻找
            template_str = pipeline_state.get("template", "")
            if not template_str:
                raise ValueError("TemplateRuntime requires a 'template' string from its input or pipeline state.")
            
        # 模板渲染需要访问全局上下文
        rendered_string = await render_template(template_str, context)
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时。"""
    async def execute(self, step_input: Dict[str, Any], pipeline_state: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # LLM 的 prompt 通常是上一步的输出
        prompt_template_str = step_input.get("prompt", step_input.get("output", ""))

        if not prompt_template_str:
             # 回退到 pipeline_state 寻找
            prompt_template_str = pipeline_state.get("prompt", pipeline_state.get("output", ""))
            if not prompt_template_str:
                raise ValueError("LLMRuntime requires a 'prompt' or 'output' string from its input or pipeline state.")

        rendered_prompt = await render_template(prompt_template_str, context)
        
        # 模拟LLM调用
        await asyncio.sleep(0.1)
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        # 返回LLM的核心数据
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}