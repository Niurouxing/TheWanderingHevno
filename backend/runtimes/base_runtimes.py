# backend/runtimes/base_runtimes.py
import asyncio 
from typing import Dict, Any, Optional
from backend.core.interfaces import RuntimeInterface # <-- 从新位置导入
from backend.core.types import ExecutionContext

class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}

class LLMRuntime(RuntimeInterface):
    """从自己的 config 中获取已经渲染好的 prompt。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, pipeline_state: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        rendered_prompt = config.get("prompt")

        # 也可以从管道状态中获取输入，以实现链式调用
        if not rendered_prompt and pipeline_state:
            rendered_prompt = pipeline_state.get("output", "")
        
        if not rendered_prompt:
            raise ValueError("LLMRuntime requires a 'prompt' in its config or an 'output' from the previous step.")

        # 模拟 LLM API 调用延迟
        await asyncio.sleep(0.1)
        
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}

class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        # 修改的是可变的 ExecutionContext.world_state
        context.world_state[variable_name] = value_to_set
        
        # 这个运行时通常没有自己的输出，只是产生副作用
        return {}