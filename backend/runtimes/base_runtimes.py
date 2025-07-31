# backend/runtimes/base_runtimes.py
import asyncio 
from backend.core.runtime import RuntimeInterface
# 从新的中心位置导入类型
from backend.core.types import ExecutionContext
from typing import Dict, Any

class InputRuntime(RuntimeInterface):
    """我只关心 step_input。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        return {"output": step_input.get("value", "")}


class LLMRuntime(RuntimeInterface):
    """我需要一个已经完全渲染好的 prompt。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        pipeline_state = kwargs.get("pipeline_state", {})
        # 宏预处理器已经处理了模板，我们直接获取最终的 prompt
        rendered_prompt = step_input.get("prompt", step_input.get("output", 
                                 pipeline_state.get("prompt", "")))

        if not rendered_prompt:
            raise ValueError("LLMRuntime requires a 'prompt' or 'output' string.")

        # 模拟 LLM API 调用延迟
        await asyncio.sleep(0.1)
        
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}

# 演示一个只关心 context 的新 Runtime
class SetWorldVariableRuntime(RuntimeInterface):
    """设置一个持久化的世界变量。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        context = kwargs.get("context")
        variable_name = step_input.get("variable_name")
        value_to_set = step_input.get("value")
        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name'.")
        # 修改的是可变的 world_state
        context.world_state[variable_name] = value_to_set
        return {}