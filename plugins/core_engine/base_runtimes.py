# backend/runtimes/base_runtimes.py
import asyncio 
from typing import Dict, Any, Optional
from backend.core.interfaces import RuntimeInterface
from backend.core.registry import runtime_registry 
from backend.core.state import ExecutionContext
from backend.llm.models import LLMResponse, LLMRequestFailedError

@runtime_registry.register("system.input") 
class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}


@runtime_registry.register("system.set_world_var")
class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        # === LOGGING START ===
        print(f"\n--- [RUNTIME set_world_var] Setting '{variable_name}' to: {value_to_set}")
        print(f"--- [RUNTIME set_world_var] world_state before: {context.shared.world_state}")
        # === LOGGING END ===
        
        context.shared.world_state[variable_name] = value_to_set
        
        # === LOGGING START ===
        print(f"--- [RUNTIME set_world_var] world_state after: {context.shared.world_state}\n")
        # === LOGGING END ===
        
        return {}