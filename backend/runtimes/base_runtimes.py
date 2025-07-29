# backend/runtimes/base_runtimes.py
from backend.core.runtime import RuntimeInterface, ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点的运行时。现在它会忽略任何上游管道输入，只返回自己的配置值。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 优先从 node_data['node_data'] (原始配置) 中获取
        original_node_data = node_data.get("node_data", {})
        if "value" in original_node_data:
            return {"output": original_node_data["value"]}
        
        # 如果原始配置中没有，再从当前输入中获取（兼容旧的单元测试）
        return {"output": node_data.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """通用的模板渲染运行时。它会查找 'template' 字段。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 优先从上一步的输出中获取模板，如果找不到，再从节点原始配置中获取
        template_str = node_data.get("template", node_data.get("node_data", {}).get("template", ""))
        
        rendered_string = await render_template(template_str, context)
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时。它会查找 'prompt' 字段。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 优先从上一步的输出中获取prompt（可能是上一步TemplateRuntime生成的）
        # 如果没有，则从节点原始数据中获取prompt模板
        prompt_template_str = node_data.get("prompt", node_data.get("node_data", {}).get("prompt", ""))
        
        # 如果上一步的输出是 "output" 字段，也接受它作为 prompt
        if not prompt_template_str and "output" in node_data:
            prompt_template_str = node_data["output"]

        if not prompt_template_str:
            raise ValueError("LLMRuntime requires a 'prompt' string from its input or configuration.")

        rendered_prompt = await render_template(prompt_template_str, context)
        
        # --- 模拟LLM调用 ---
        print(f"  - Calling LLM with Prompt: {rendered_prompt}")
        await asyncio.sleep(0.1) # 缩短测试时间
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}