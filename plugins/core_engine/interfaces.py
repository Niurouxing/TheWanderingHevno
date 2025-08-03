# plugins/core_engine/interfaces.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .contracts import ExecutionContext

class SubGraphRunner(ABC):
    """定义执行子图能力的抽象接口。"""
    @abstractmethod
    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

class RuntimeInterface(ABC):
    """定义所有运行时必须实现的接口。"""
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        pipeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass