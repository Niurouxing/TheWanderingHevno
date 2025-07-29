# backend/runtimes/base_runtimes.py
import asyncio 
from backend.core.runtime import RuntimeInterface, ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any

class InputRuntime(RuntimeInterface):
    """我只关心 step_input。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        return {"output": step_input.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """我需要 step_input (或 pipeline_state) 来获取模板，需要 context 来渲染。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        pipeline_state = kwargs.get("pipeline_state", {})
        context = kwargs.get("context")

        template_str = step_input.get("template", pipeline_state.get("template", ""))
        if not template_str:
            raise ValueError("TemplateRuntime requires a 'template' string.")
            
        rendered_string = await render_template(template_str, context)
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """我需要 step_input/pipeline_state 来获取 prompt，需要 context 来渲染。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        pipeline_state = kwargs.get("pipeline_state", {})
        context = kwargs.get("context")
        
        prompt_template_str = step_input.get("prompt", step_input.get("output", 
                                pipeline_state.get("prompt", "")))
        if not prompt_template_str:
            raise ValueError("LLMRuntime requires a 'prompt' or 'output' string.")

        rendered_prompt = await render_template(prompt_template_str, context)
        
        # 恢复异步行为，模拟 LLM API 调用延迟
        await asyncio.sleep(0.1)  # <--- 恢复这一行
        
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}

# 演示一个只关心 context 的新 Runtime
class SetGlobalVariableRuntime(RuntimeInterface):
    """我只关心 step_input 和 context，用于将输入设置为全局变量。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        context = kwargs.get("context")
        
        variable_name = step_input.get("variable_name")
        value_to_set = step_input.get("value")

        if not variable_name:
            raise ValueError("SetGlobalVariableRuntime requires 'variable_name'.")

        if context:
            context.global_vars[variable_name] = value_to_set
            
        # 这个 Runtime 不产生新的直接输出，所以返回空字典
        # 它的作用完全是副作用（修改 context）
        return {}