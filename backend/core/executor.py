# backend/core/executor.py
import asyncio
from graphlib import TopologicalSorter, CycleError
from typing import Dict, Any, Set

from backend.models import Graph
from backend.core.registry import RuntimeRegistry
from backend.core.runtime import ExecutionContext

class GraphExecutor:
    def __init__(self, registry: RuntimeRegistry):
        self.registry = registry

    async def execute(self, graph: Graph) -> Dict[str, Any]:
        node_map = {node.id: node for node in graph.nodes}
        # 构建一个反向依赖图，方便查找父节点
        predecessors = {node.id: [] for node in graph.nodes}
        for edge in graph.edges:
            predecessors[edge.target].append(edge.source)
        sorter = TopologicalSorter()
        
        # 2. 完成所有的 add 操作
        for node in graph.nodes:
            sorter.add(node.id)

        for edge in graph.edges:
            sorter.add(edge.target, edge.source)

        # 3. 在所有 add 操作后，调用 prepare 一次
        try:
            sorter.prepare()
        except CycleError as e:
            # CycleError 被正确捕获
            raise ValueError(f"Graph has a cycle: {e.args[1]}") from e

        exec_context = ExecutionContext(
            state={},
            graph=graph,
            function_registry={}
        )

        # 3. 循环执行，直到所有节点完成
        while sorter.is_active():
            ready_nodes_ids = sorter.get_ready()
            
            tasks = []
            nodes_to_execute_ids = [] # 只包含真正要执行的节点

            for node_id in ready_nodes_ids:
                # 关键修复：检查上游依赖是否都成功了
                parent_ids = predecessors[node_id]
                if any(
                    exec_context.state.get(p_id, {}).get("error")
                    for p_id in parent_ids
                ):
                    # 如果任何一个父节点有错误，就跳过当前节点
                    print(f"Skipping node {node_id} due to upstream failure.")
                    # 标记为完成，但不在 state 中创建条目
                    sorter.done(node_id)
                    continue
                
                # 如果检查通过，才加入执行列表
                nodes_to_execute_ids.append(node_id)
                node = node_map[node_id]
                tasks.append(self._execute_node(node, exec_context))

            if not tasks: # 如果本轮没有可执行的任务，继续下一轮
                continue

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 5. 处理执行结果并更新状态
            for i, result in enumerate(results):
                node_id = ready_nodes_ids[i]
                if isinstance(result, Exception):
                    # 如果执行中发生异常，记录错误
                    error_message = f"Error executing node {node_id}: {result}"
                    print(error_message)
                    exec_context.state[node_id] = {"error": error_message}
                else:
                    # 否则，更新状态
                    exec_context.state[node_id] = result
                
                # 标记节点已完成，以便排序器可以找到下一批就绪节点
                sorter.done(node_id)
        
        print("Graph execution finished.")
        return exec_context.state

    async def _execute_node(self, node, context: ExecutionContext) -> Dict[str, Any]:
        """
        一个辅助方法，用于执行单个节点。
        现在支持单个runtime或一个runtime管道。
        """
        node_id = node.id
        runtime_spec = node.data.get("runtime")
        
        if not runtime_spec:
            print(f"Warning: Node {node_id} has no runtime. Skipping.")
            return {"skipped": True}

        # 将单个 runtime 字符串包装成列表，以统一处理
        if isinstance(runtime_spec, str):
            runtime_names = [runtime_spec]
        else:
            runtime_names = runtime_spec

        # 这是管道的初始输入，就是节点自身的data
        pipeline_input = node.data
        final_output = {}

        print(f"Executing node: {node_id} with runtime pipeline: {runtime_names}")
        
        for i, runtime_name in enumerate(runtime_names):
            print(f"  - Step {i+1}/{len(runtime_names)}: Running runtime '{runtime_name}'")
            try:
                runtime = self.registry.get_runtime(runtime_name)
                
                # 关键：将上一步的输出作为当前运行时的输入
                # 同时，将原始节点数据和上下文也传入，以便运行时能访问它们
                # 我们创建一个新的字典，以防运行时意外修改原始数据
                current_step_input = {**pipeline_input, "node_data": node.data}
                
                output = await runtime.execute(current_step_input, context)
                
                # 将当前步骤的输出作为下一步骤的输入
                pipeline_input = output
                final_output = output

            except Exception as e:
                # 如果管道中任何一步失败，整个节点都失败
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {e}"
                print(f"  - Error in pipeline: {error_message}")
                # 返回一个标准的错误结构
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}

        # 整个管道成功完成后，返回最后一个运行时的输出
        return final_output