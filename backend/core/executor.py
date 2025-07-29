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
        （这个逻辑是从旧的 execute 循环中提取出来的）
        """
        node_id = node.id
        runtime_name = node.data.get("runtime")
        
        if not runtime_name:
            print(f"Warning: Node {node_id} has no runtime. Skipping.")
            return {"skipped": True}

        print(f"Executing node: {node_id} with runtime: {runtime_name}")
        
        runtime = self.registry.get_runtime(runtime_name)
        
        # 注意！这里传递的是一个只读的 context.state 副本的引用
        # 运行时不应该直接修改 context，而是返回其输出
        return await runtime.execute(node.data, context)