# plugins/core_engine/runtimes/flow_runtimes.py
import asyncio
from typing import Dict, Any, List, Optional

from backend.core.utils import DotAccessibleDict
from ..contracts import RuntimeInterface, SubGraphRunner, ExecutionContext
from ..evaluation import evaluate_data, evaluate_expression, build_evaluation_context


class ExecuteRuntime(RuntimeInterface):
    """
    system.execute: 对一个字符串形式的宏代码进行二次求值和执行。
    作为宏系统的终极“逃生舱口”。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            return {"output": code_to_execute}

        eval_context = build_evaluation_context(context)
        lock = context.shared.global_write_lock
        result = await evaluate_expression(code_to_execute, eval_context, lock)
        return {"output": result}


class CallRuntime(RuntimeInterface):
    """
    system.flow.call: 调用并执行一个可复用的子图。
    """
    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("CallRuntime requires a SubGraphRunner.")
            
        graph_name = config.get("graph")
        if not graph_name:
            raise ValueError("CallRuntime requires a 'graph' name in its config.")
            
        using_inputs = config.get("using", {})
        
        inherited_inputs = {
            placeholder_name: {"output": value}
            for placeholder_name, value in using_inputs.items()
        }

        subgraph_results = await subgraph_runner.execute_graph(
            graph_name=graph_name,
            parent_context=context,
            inherited_inputs=inherited_inputs
        )
        
        return {"output": subgraph_results}


class MapRuntime(RuntimeInterface):
    """
    system.flow.map: 对一个列表进行并行迭代，为每个元素执行一次子图。
    """
    template_fields = ["using", "collect"]

    @classmethod
    def get_dependency_config(cls) -> Dict[str, Any]:
        """
        我们告诉解析器，'using' 和 'collect' 字段包含的 'nodes.xxx' 
        是在子图的上下文中，不应被视为主图的依赖。
        """
        return {
            "ignore_fields": ["using", "collect"]
        }

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        if not subgraph_runner:
            raise ValueError("MapRuntime requires a SubGraphRunner.")

        list_to_iterate = config.get("list")
        graph_name = config.get("graph")
        using_template = config.get("using", {})
        collect_template = config.get("collect")

        if not isinstance(list_to_iterate, list):
            raise TypeError(f"MapRuntime 'list' field must be a list, got {type(list_to_iterate).__name__}.")
        if not graph_name:
            raise ValueError("MapRuntime requires a 'graph' name in its config.")

        tasks = []
        base_eval_context = build_evaluation_context(context)
        lock = context.shared.global_write_lock

        for index, item in enumerate(list_to_iterate):
            using_eval_context = {
                **base_eval_context,
                "source": DotAccessibleDict({"item": item, "index": index})
            }
            
            evaluated_using = await evaluate_data(using_template, using_eval_context, lock)
            inherited_inputs = {
                placeholder: {"output": value}
                for placeholder, value in evaluated_using.items()
            }
            
            task = asyncio.create_task(
                subgraph_runner.execute_graph(
                    graph_name=graph_name,
                    parent_context=context,
                    inherited_inputs=inherited_inputs
                )
            )
            tasks.append(task)
        
        subgraph_results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        
        if collect_template is not None:
            collected_outputs = []
            for result in subgraph_results:
                collect_eval_context = build_evaluation_context(context)
                collect_eval_context["nodes"] = DotAccessibleDict(result)
                
                collected_value = await evaluate_data(collect_template, collect_eval_context, lock)
                collected_outputs.append(collected_value)
            
            return {"output": collected_outputs}
        else:
            return {"output": subgraph_results}