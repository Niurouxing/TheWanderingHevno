# plugins/core_engine/evaluation_service.py
import asyncio
from typing import Any, Dict, Optional

from .contracts import ExecutionContext, MacroEvaluationServiceInterface
from .evaluation import build_evaluation_context as build_context_impl
from .evaluation import evaluate_data as evaluate_data_impl

class MacroEvaluationService(MacroEvaluationServiceInterface):
    """
    实现了宏求值接口，作为对 evaluation.py 中复杂逻辑的封装。
    """
    def build_context(
        self,
        exec_context: ExecutionContext,
        pipe_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        代理调用原始的 build_evaluation_context 函数。
        """
        return build_context_impl(exec_context, pipe_vars)

    async def evaluate(
        self,
        data: Any,
        eval_context: Dict[str, Any],
        lock: asyncio.Lock
    ) -> Any:
        """
        代理调用原始的 evaluate_data 函数。
        """
        return await evaluate_data_impl(data, eval_context, lock)