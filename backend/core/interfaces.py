# backend/core/interfaces.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from backend.core.types import ExecutionContext


class SubGraphRunner(ABC):
    """
    一个抽象接口，定义了执行子图的能力。
    这是引擎必须提供给需要回调的运行时的服务。
    """
    @abstractmethod
    async def execute_graph(
        self,
        graph_name: str,
        context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

class RuntimeInterface(ABC):
    """
    重新定义的运行时接口。
    它现在只依赖于 ExecutionContext 和可选的 SubGraphRunner。
    它不再知道 ExecutionEngine 的存在。
    """
    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        context: ExecutionContext,
        subgraph_runner: Optional[SubGraphRunner] = None,
        # 我们可以保留 pipeline_state 以支持节点内管道
        pipeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        :param config: 已求值的配置。
        :param context: 当前的执行上下文 (包含 world_state 等)。
        :param subgraph_runner: 一个可选的回调接口，用于执行子图。
        :param pipeline_state: 节点内上一步的输出。
        """
        pass
