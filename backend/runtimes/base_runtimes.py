# backend/runtimes/base_runtimes.py
from backend.core.runtime import RuntimeInterface, ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点。它只关心自己的配置值。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 逻辑变得非常简单
        return {"output": node_data.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """通用的模板渲染运行时。它会在输入中查找 'template' 字段。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        template_str = node_data.get("template", "")
        if not template_str:
            raise ValueError("TemplateRuntime requires a 'template' string from its input.")
            
        rendered_string = await render_template(template_str, context)
        # 修复：只返回它生成的核心输出，而不是合并所有输入
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时。它会查找 'prompt' 或 'output' 字段作为输入。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        prompt_template_str = node_data.get("prompt", node_data.get("output", ""))

        if not prompt_template_str:
            raise ValueError("LLMRuntime requires a 'prompt' or 'output' string from its input.")

        rendered_prompt = await render_template(prompt_template_str, context)
        
        await asyncio.sleep(0.1)
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        # 修复：同样，只返回LLM生成的核心数据
        return {"output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}