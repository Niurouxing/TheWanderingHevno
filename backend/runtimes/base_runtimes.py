# backend/runtimes/base_runtimes.py
from backend.core.runtime import RuntimeInterface, ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点的运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        return {"output": node_data.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """通用的模板渲染运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        template_str = node_data.get("template", "")
        rendered_string = await render_template(template_str, context)
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        prompt_template_str = node_data.get("prompt", "")

        print(f"\n[DEBUG] In LLMRuntime for node, context.state is: {context.state}\n")
        
        
        # 使用新的渲染函数
        rendered_prompt = await render_template(prompt_template_str, context)
        
        # --- 模拟LLM调用 ---
        print(f"  - Calling LLM with Prompt: {rendered_prompt}")
        await asyncio.sleep(1) # 模拟网络延迟
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}