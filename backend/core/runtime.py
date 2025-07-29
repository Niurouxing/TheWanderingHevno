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
    定义所有运行时都必须遵守的接口。
    这个接口设计了一个混合模型，以同时支持简单的转换流水线和复杂的数据增强。
    """
    @abstractmethod
    async def execute(
        self, 
        step_input: Dict[str, Any], 
        pipeline_state: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。

        Args:
            step_input (Dict[str, Any]):
                上一个 Runtime 的直接输出。
                对于流水线中的第一个 Runtime，这是节点的初始 `data` 字段。
                这遵循“转换/覆盖”模型，适合简单的、一步接一步的数据处理。

            pipeline_state (Dict[str, Any]):
                到当前步骤为止，所有先前步骤输出的累积状态（合并结果）。
                它也以节点的初始 `data` 字段作为起点。
                这遵循“增强/组合”模型，允许 Runtime 访问流水线中任何早期步骤产生的数据，
                从而实现更复杂的、有状态的逻辑，而无需在 Runtime 之间手动传递所有内容。

            context (ExecutionContext):
                全局图执行上下文，包含所有已完成节点的状态 (`context.state`)、
                全局变量 (`context.vars`) 等。

        Returns:
            Dict[str, Any]:
                当前 Runtime 的直接输出。这个返回值将成为下一个 Runtime 的 `step_input`，
                并且它也会被合并到 `pipeline_state` 中。
        """
        pass