# backend/core/runtime.py 
from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

# 避免循环导入
if TYPE_CHECKING:
    from backend.core.engine import ExecutionEngine
    from backend.core.types import ExecutionContext

class RuntimeInterface(ABC):
    """
    定义所有运行时都必须遵守的接口。
    """
    @abstractmethod
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        
        :param config: 经过宏求值后的、该运行时专属的配置字典。
        :param kwargs: 其他上下文信息, 如 pipeline_state, context, engine。
                       对于需要特殊求值逻辑的运行时(如map), 也会包含 evaluate_data_func
        """
        pass