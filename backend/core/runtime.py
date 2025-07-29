# backend/core/runtime.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field 
import asyncio
from datetime import datetime, timezone


class ExecutionContext(BaseModel):
    # 之前已有的
    state: Dict[str, Any] 
    graph: Any
    
    # --- 新增的全局变量 ---
    # 会话级的元数据
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,
    })
    
    # 全局变量存储，可以在图执行过程中被修改和读取
    global_vars: Dict[str, Any] = Field(default_factory=dict)

    # 我们之前构想的函数注册表
    function_registry: Dict[str, Callable] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True
    }

class RuntimeInterface(ABC):
    """定义所有运行时都必须遵守的接口 (使用抽象基类)"""
    @abstractmethod
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        - node_data: 节点自身的data字段。
        - context: 当前的执行上下文。
        - 返回值: 该节点的输出，将被存入全局状态。
        """
        pass