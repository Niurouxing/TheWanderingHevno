# plugins/core_engine/runtimes/base_runtimes.py

import logging
from typing import Dict, Any


from ..interfaces import RuntimeInterface
from backend.core.contracts import ExecutionContext

logger = logging.getLogger(__name__)


class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}


class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        logger.debug(f"Setting world_state['{variable_name}'] to: {value_to_set}")
        context.shared.world_state[variable_name] = value_to_set
        
        return {}