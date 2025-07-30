# backend/core/runtime.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class RuntimeInterface(ABC):
    """
    定义所有运行时都必须遵守的接口。
    这是一个纯粹的抽象，不依赖于任何具体的上下文实现。
    """
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        
        通过关键字参数 (kwargs) 接收所有上下文信息。
        具体的可用关键字参数由 ExecutionEngine 在调用时提供。
        """
        pass