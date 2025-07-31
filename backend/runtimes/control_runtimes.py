# backend/runtimes/control_runtimes.py
import asyncio
from typing import Dict, Any, List

from backend.core.runtime import RuntimeInterface
# 导入所有需要的核心组件
from backend.core.evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from backend.core.types import ExecutionContext
from backend.core.engine import ExecutionEngine
from backend.core.utils import DotAccessibleDict


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


# --- 新增的 MapRuntime ---
class MapRuntime(RuntimeInterface):
    """
    实现并行迭代 (Fan-out / Scatter-Gather)。
    将一个子图并发地应用到输入列表的每个元素上。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        # --- 1. 准备阶段 (Preparation) ---
        engine: ExecutionEngine = kwargs.get("engine")
        context: ExecutionContext = kwargs.get("context")
        
        if not engine or not context:
            raise ValueError("MapRuntime requires 'engine' and 'context' in kwargs.")

        # `list` 和 `graph` 已经被引擎预先计算好
        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        # `using` 和 `collect` 是未计算的模板
        using_template = config.get("using", {})
        collect_expression_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"system.map 'list' field must be a list, but got {type(list_to_iterate).__name__}")
        if not graph_name:
            raise ValueError("system.map requires a 'graph' name in its config.")

        graph_collection = context.initial_snapshot.graph_collection.root
        subgraph_def = graph_collection.get(graph_name)
        if not subgraph_def:
            raise ValueError(f"Subgraph '{graph_name}' for system.map not found in graph collection.")

        # --- 2. 分发/任务创建阶段 (Scatter / Task Creation) ---
        tasks = []
        base_eval_context = build_evaluation_context(context)

        for index, item in enumerate(list_to_iterate):
            # a. 创建包含 `source` 对象的临时上下文，用于求值 `using`
            using_eval_context = {
                **base_eval_context,
                "source": DotAccessibleDict({"item": item, "index": index})
            }
            
            # b. 求值 `using` 字典
            evaluated_using = await evaluate_data(using_template, using_eval_context)
            inherited_inputs = {
                placeholder: {"output": value}
                for placeholder, value in evaluated_using.items()
            }
            
            # --- 【核心修正】---
            # c. 创建一个真正共享状态的、隔离的执行上下文
            # 先创建一个干净的上下文，然后用引用覆盖共享字段
            iteration_context = ExecutionContext.from_snapshot(context.initial_snapshot)
            
            # 【关键】确保 world_state 和 internal_vars (含锁) 是同一个对象引用，而不是副本
            iteration_context.world_state = context.world_state
            iteration_context.internal_vars = context.internal_vars
            iteration_context.session_info = context.session_info
            
            # 【关键】确保 node_states 是隔离的，每个子图有自己的节点结果
            iteration_context.node_states = {}

            # d. 创建子图执行任务
            task = asyncio.create_task(
                engine._execute_graph(
                    graph_def=subgraph_def,
                    context=iteration_context,
                    inherited_inputs=inherited_inputs
                )
            )
            tasks.append(task)
        
        print(f"  -> Mapping '{graph_name}' across {len(tasks)} items.")

        # --- 3. 执行与等待阶段 (Execution & Wait) ---
        subgraph_results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        print(f"  <- All {len(tasks)} mapped executions finished.")
        
        # --- 4. 聚合阶段 (Gather) ---
        if collect_expression_template:
            # 如果提供了 `collect`，则对每个结果进行二次求值
            collected_outputs = []
            for result in subgraph_results:
                # 为 `collect` 表达式创建局部求值上下文
                # 关键: `nodes` 指向当前子图的结果
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                # 求值 collect 表达式
                collected_value = await evaluate_data(collect_expression_template, collect_eval_context)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            # 默认行为：返回每个子图的完整结果列表
            return {"output": subgraph_results}