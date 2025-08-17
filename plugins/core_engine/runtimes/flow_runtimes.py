# plugins/core_engine/runtimes/flow_runtimes.py
import asyncio
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, Field

from backend.core.utils import DotAccessibleDict
from ..contracts import RuntimeInterface, SubGraphRunner, ExecutionContext
from ..evaluation import evaluate_data, evaluate_expression, build_evaluation_context


class ExecuteRuntime(RuntimeInterface):
    """
    system.execute: 对一个字符串形式的宏代码进行二次求值和执行。
    作为宏系统的终极“逃生舱口”。
    """
    class ConfigModel(BaseModel):
        code: str = Field(..., description="包含要执行的宏代码的字符串。例如 '{{ moment.player_hp -= 10 }}'。")

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(
        self, 
        config: Dict[str, Any], 
        context: ExecutionContext, 
        pipeline_state: Optional[Dict[str, Any]] = None, 
        **kwargs
    ) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            code_to_execute = validated_config.code

            if not isinstance(code_to_execute, str):
                return {"output": code_to_execute}

            eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
            lock = context.shared.global_write_lock
            result = await evaluate_expression(code_to_execute, eval_context, lock)
            return {"output": result}
        except Exception as e:
            return {"error": f"Invalid configuration or execution error in system.execute: {e}"}

class CallRuntime(RuntimeInterface):
    """
    system.flow.call: 调用并执行一个可复用的子图。
    """
    class ConfigModel(BaseModel):
        graph: str = Field(..., description="要调用的子图的名称。")
        using: Optional[Dict[str, Any]] = Field(
            default=None, 
            description="一个字典，将值传递给子图的输入节点。键是子图中的节点ID，值是该节点的输出。"
        )
    
    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            if not subgraph_runner:
                raise ValueError("CallRuntime requires a SubGraphRunner to be available.")
                
            inherited_inputs = {
                placeholder_name: {"output": value}
                for placeholder_name, value in (validated_config.using or {}).items()
            }

            subgraph_results = await subgraph_runner.execute_graph(
                graph_name=validated_config.graph,
                parent_context=context,
                inherited_inputs=inherited_inputs
            )
            
            return {"output": subgraph_results}
        except Exception as e:
            return {"error": f"Error during system.flow.call: {e}"}


class MapRuntime(RuntimeInterface):
    """
    system.flow.map: 对一个列表进行并行迭代，为每个元素执行一次子图。
    """
    class ConfigModel(BaseModel):
        list: List[Any] = Field(..., description="要迭代的列表。")
        graph: str = Field(..., description="为每个列表项执行的子图的名称。")
        using: Optional[Dict[str, Any]] = Field(
            default=None, 
            description="传递给子图的输入模板。在求值时，上下文中会额外包含 `source.item` 和 `source.index`。"
        )
        collect: Optional[Any] = Field(
            default=None, 
            description="一个宏，用于从每次子图运行的结果中聚合数据，形成最终的输出列表。"
        )

    @classmethod
    def get_config_model(cls) -> Type[BaseModel]:
        return cls.ConfigModel

    template_fields = ["using", "collect"]

    @classmethod
    def get_dependency_config(cls) -> Dict[str, Any]:
        return {
            "ignore_fields": ["using", "collect"]
        }

    async def execute(self, config: Dict[str, Any], context: ExecutionContext, subgraph_runner: Optional[SubGraphRunner] = None, **kwargs) -> Dict[str, Any]:
        try:
            validated_config = self.ConfigModel.model_validate(config)
            if not subgraph_runner:
                raise ValueError("MapRuntime requires a SubGraphRunner.")

            list_to_iterate = validated_config.list
            graph_name = validated_config.graph
            using_template = config.get("using", {}) # Get raw from config for templating
            collect_template = config.get("collect")

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
        except Exception as e:
            return {"error": f"Error in system.flow.map: {e}"}