# plugins/core_engine/runtimes/control_runtimes.py

from typing import Dict, Any, List, Optional
import asyncio


from ..interfaces import RuntimeInterface, SubGraphRunner
from ..evaluation import evaluate_data, evaluate_expression, build_evaluation_context
from ..utils import DotAccessibleDict
from backend.core.contracts import ExecutionContext


class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            return {"output": code_to_execute}

        eval_context = build_evaluation_context(context)
        # --- 修正: 从共享上下文中获取并传递锁 ---
        lock = context.shared.global_write_lock
        result = await evaluate_expression(code_to_execute, eval_context, lock)
        return {"output": result}


class CallRuntime(RuntimeInterface):
    """执行一个子图。"""
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("CallRuntime requires a SubGraphRunner.")
            
        graph_name = config.get("graph")
        using_inputs = config.get("using", {})
        
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        # 调用 subgraph_runner，它会负责创建正确的子上下文
        subgraph_results = await subgraph_runner.execute_graph(
            graph_name=graph_name,
            parent_context=context, # 传递当前的上下文
            inherited_inputs=inherited_inputs
        )
        
        return {"output": subgraph_results}


class MapRuntime(RuntimeInterface):
    """并行迭代。"""
    template_fields = ["using", "collect"]

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("MapRuntime requires a SubGraphRunner.")

        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        using_template = config.get("using", {})
        collect_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"system.map 'list' field must be a list...")

        tasks = []
        base_eval_context = build_evaluation_context(context)
        lock = context.shared.global_write_lock

        for index, item in enumerate(list_to_iterate):
            # a. 创建包含 `source` 的临时上下文，用于求值 `using`
            using_eval_context = {
                **base_eval_context,
                "source": DotAccessibleDict({"item": item, "index": index})
            }
            
            # b. 求值 `using` 字典 (需要传递锁)
            evaluated_using = await evaluate_data(using_template, using_eval_context, lock)
            inherited_inputs = {
                placeholder: {"output": value}
                for placeholder, value in evaluated_using.items()
            }
            
            # c. 创建子图执行任务
            #    subgraph_runner.execute_graph 会处理子上下文的创建
            task = asyncio.create_task(
                subgraph_runner.execute_graph(
                    graph_name=graph_name,
                    parent_context=context,
                    inherited_inputs=inherited_inputs
                )
            )
            tasks.append(task)
        
        subgraph_results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        
        # d. 聚合阶段
        if collect_template:
            collected_outputs = []
            for result in subgraph_results:
                # `nodes` 指向当前子图的结果
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                collected_value = await evaluate_data(collect_template, collect_eval_context, lock)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            return {"output": subgraph_results}