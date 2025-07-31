# backend/runtimes/control_runtimes.py
from backend.core.runtime import RuntimeInterface
from backend.core.evaluation import evaluate_expression, build_evaluation_context
from typing import Dict, Any

class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        context = kwargs.get("context")

        code_to_execute = step_input.get("code")

        if not isinstance(code_to_execute, str):
            # 如果 code 字段不是字符串 (可能是 None 或其他类型)，
            # 我们可以选择静默返回或抛出错误。这里选择静默。
            return {"output": code_to_execute}

        # 构建当前的执行上下文
        eval_context = build_evaluation_context(context)

        # 进行二次求值
        result = await evaluate_expression(code_to_execute, eval_context)

        return {"output": result}

# 未来，system.map 和 system.call 也可以移到这里。