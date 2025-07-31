# backend/runtimes/control_runtimes.py
from backend.core.runtime import RuntimeInterface
from backend.core.evaluation import evaluate_expression, build_evaluation_context
from typing import Dict, Any

class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        context = kwargs.get("context")
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            return {"output": code_to_execute}

        # 构建当前的执行上下文
        eval_context = build_evaluation_context(context)

        # 进行二次求值
        result = await evaluate_expression(code_to_execute, eval_context)

        return {"output": result}

# 未来，system.map 和 system.call 也将放在这里