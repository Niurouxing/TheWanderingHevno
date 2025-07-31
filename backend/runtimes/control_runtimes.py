# backend/runtimes/control_runtimes.py
from backend.core.runtime import RuntimeInterface
from backend.core.evaluation import evaluate_expression, build_evaluation_context
from backend.core.types import ExecutionContext
from backend.core.engine import ExecutionEngine # 导入引擎以进行递归调用
from typing import Dict, Any

class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        context: ExecutionContext = kwargs.get("context")
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            # 如果不是字符串（例如，宏求值后变成了数字或对象），直接返回
            return {"output": code_to_execute}

        # 构建当前的执行上下文
        eval_context = build_evaluation_context(context)
        # 进行二次求值
        result = await evaluate_expression(code_to_execute, eval_context)
        return {"output": result}


class CallRuntime(RuntimeInterface):
    """
    执行一个子图。这是代码复用和逻辑分层的基础。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        engine: ExecutionEngine = kwargs.get("engine")
        context: ExecutionContext = kwargs.get("context")
        
        if not engine or not context:
            raise ValueError("CallRuntime requires 'engine' and 'context' in kwargs.")
            
        graph_name = config.get("graph")
        if not graph_name:
            raise ValueError("system.call requires a 'graph' name in its config.")
            
        # `using` 字典的值在此刻已经被宏系统求值完毕
        using_inputs = config.get("using", {})
        
        # 1. 找到子图的定义
        graph_collection = context.initial_snapshot.graph_collection.root
        subgraph_def = graph_collection.get(graph_name)
        if not subgraph_def:
            raise ValueError(f"Subgraph '{graph_name}' not found in graph collection.")

        # 2. 准备要注入的 "inherited_inputs"
        # 我们将 `using` 字典转换为标准的节点输出格式
        # e.g., 'character_input' becomes a node with result {'output': ...}
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        # 3. 递归调用执行引擎来运行子图
        print(f"  -> Calling subgraph '{graph_name}' with inputs: {list(inherited_inputs.keys())}")
        subgraph_results = await engine._execute_graph(
            graph_def=subgraph_def,
            context=context, # 传递当前的执行上下文（特别是 world_state）
            inherited_inputs=inherited_inputs
        )
        print(f"  <- Subgraph '{graph_name}' finished.")

        # 4. 将子图的完整结果作为此运行时的输出
        return {"output": subgraph_results}

# 未来，system.map 也将放在这里