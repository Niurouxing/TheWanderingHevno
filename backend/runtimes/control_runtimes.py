# backend/runtimes/control_runtimes.py
import asyncio
from typing import Dict, Any, List, Optional

from backend.core.interfaces import RuntimeInterface, SubGraphRunner # <-- 从新位置导入
# 导入所有需要的核心组件
from backend.core.evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from backend.core.types import ExecutionContext
from backend.core.utils import DotAccessibleDict


class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
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
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        # --- 核心变化 ---
        if not subgraph_runner:
            raise ValueError("CallRuntime requires a SubGraphRunner to be provided.")
            
        graph_name = config.get("graph")
        if not graph_name:
            raise ValueError("system.call requires a 'graph' name in its config.")
            
        # `using` 字典的值在此刻已经被宏系统求值完毕
        using_inputs = config.get("using", {})
        
        # 1. 准备要注入的 "inherited_inputs"
        # 我们将 `using` 字典转换为标准的节点输出格式
        # e.g., 'character_input' becomes a node with result {'output': ...}
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        # --- 使用注入的服务，而不是整个引擎 ---
        print(f"  -> Calling subgraph '{graph_name}' with inputs: {list(inherited_inputs.keys())}")
        subgraph_results = await subgraph_runner.execute_graph(
            graph_name=graph_name,
            context=context,
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
    template_fields = ["using", "collect"]

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("MapRuntime requires a SubGraphRunner to be provided.")

        # --- 1. 准备阶段 (Preparation) ---
        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        using_template = config.get("using", {})
        collect_expression_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"system.map 'list' field must be a list, but got {type(list_to_iterate).__name__}")
        if not graph_name:
            raise ValueError("system.map requires a 'graph' name in its config.")
        
        # --- 2. 分发/任务创建阶段 (Scatter / Task Creation) ---
        tasks = []
        
        # --- 【关键修正】---
        # 将被误删的这行代码加回来！
        base_eval_context = build_evaluation_context(context)

        for index, item in enumerate(list_to_iterate):
            # a. 创建包含 `source` 对象的临时上下文
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
            
            # c. 手动创建一个新的、部分共享的 ExecutionContext
            iteration_context = ExecutionContext(
                initial_snapshot=context.initial_snapshot,
                node_states={}, 
                world_state={}, # 这是一个临时的、将被忽略的空字典
                internal_vars=context.internal_vars.copy(), # 复制 internal_vars 以便独立修改
                run_vars=context.run_vars,
                session_info=context.session_info
            )
            # 【核心】将主上下文的 world_state 作为权威引用注入
            iteration_context.internal_vars['__world_state_override__'] = context.world_state

            # d. 创建子图执行任务
            task = asyncio.create_task(
                subgraph_runner.execute_graph(
                    graph_name=graph_name,
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
            collected_outputs = []
            for result in subgraph_results:
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                collected_value = await evaluate_data(collect_expression_template, collect_eval_context)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            return {"output": subgraph_results}