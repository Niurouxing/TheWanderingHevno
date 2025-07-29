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
    """
    定义所有运行时都必须遵守的接口，采用灵活的关键字参数设计。
    """
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        
        通过关键字参数 (kwargs) 接收所有上下文信息，开发者可以按需取用。
        
        核心的可用关键字参数包括:
        - `step_input` (Dict[str, Any]): 上一个 Runtime 的直接输出。
        - `pipeline_state` (Dict[str, Any]): 节点内到当前步骤为止的累积状态。
        - `context` (ExecutionContext): 全局图执行上下文。
        - `node` (GenericNode): 当前正在执行的节点模型实例 (可选，但非常有用)。
        
        一个 Runtime 必须返回一个字典，这个字典将成为下一个 Runtime 的 `step_input`，
        并被合并到 `pipeline_state` 中。如果一个 Runtime 只是为了修改上下文（例如设置全局变量），
        它可以返回一个空字典 `{}`。

        示例:
            class MyRuntime(RuntimeInterface):
                async def execute(self, **kwargs) -> Dict[str, Any]:
                    step_input = kwargs.get("step_input", {})
                    context = kwargs.get("context")
                    if context:
                        # ... do something with context ...
                    return {"new_output": "value"}
        """
        pass