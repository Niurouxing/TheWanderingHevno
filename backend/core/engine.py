import asyncio
from enum import Enum, auto
from typing import Dict, Any, Set, List
from collections import defaultdict

from backend.models import Graph, GenericNode
from backend.core.registry import RuntimeRegistry
from backend.core.runtime import ExecutionContext


class NodeState(Enum):
    """定义节点在执行过程中的所有可能状态。"""
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    SKIPPED = auto()

class GraphRun:
    """管理一次图执行的所有状态。"""
    def __init__(self, graph: Graph):
        self.graph = graph
        self.node_map: Dict[str, GenericNode] = {n.id: n for n in graph.nodes}
        self.node_states: Dict[str, NodeState] = {}
        self.node_results: Dict[str, Dict[str, Any]] = {}

        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.subscribers: Dict[str, Set[str]] = defaultdict(set)

        self._build_dependency_graph()
        self._initialize_node_states()

    def _build_dependency_graph(self):
        for edge in self.graph.edges:
            self.dependencies[edge.target].add(edge.source)
            self.subscribers[edge.source].add(edge.target)

        # 改进后的环路检测
        visiting = set()  # 存储当前递归路径上的节点
        visited = set()   # 存储所有已访问过的节点

        def detect_cycle_util(node_id, path):
            visiting.add(node_id)
            visited.add(node_id)
            
            for neighbour in self.dependencies.get(node_id, []):
                if neighbour in visiting:
                    # 发现了环路
                    cycle_path = " -> ".join(path + [neighbour])
                    raise ValueError(f"Cycle detected in graph: {cycle_path}")
                if neighbour not in visited:
                    detect_cycle_util(neighbour, path + [node_id])
            
            visiting.remove(node_id)

        for node_id in self.node_map:
            if node_id not in visited:
                try:
                    detect_cycle_util(node_id, [node_id])
                except ValueError as e:
                    # 重新抛出，让上层能捕获到更清晰的错误
                    raise e

    def _initialize_node_states(self):
        for node_id in self.node_map:
            if not self.dependencies[node_id]:
                self.node_states[node_id] = NodeState.READY
            else:
                self.node_states[node_id] = NodeState.PENDING
    
    def get_node(self, node_id: str) -> GenericNode:
        return self.node_map[node_id]
    def get_node_state(self, node_id: str) -> NodeState:
        return self.node_states.get(node_id)
    def set_node_state(self, node_id: str, state: NodeState):
        self.node_states[node_id] = state
    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        self.node_results[node_id] = result
    def get_nodes_in_state(self, state: NodeState) -> List[str]:
        return [nid for nid, s in self.node_states.items() if s == state]
    def get_dependencies(self, node_id: str) -> Set[str]:
        return self.dependencies[node_id]
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers[node_id]
    def get_execution_context(self) -> ExecutionContext:
        return ExecutionContext(state=self.node_results, graph=self.graph)
    def get_final_state(self) -> Dict[str, Any]:
        return self.node_results


class ExecutionEngine:
    """这是新的、基于事件和工作者的执行引擎。"""
    def __init__(self, registry: RuntimeRegistry, num_workers: int = 5):
        self.registry = registry
        self.num_workers = num_workers

    async def execute(self, graph: Graph) -> Dict[str, Any]:
        run = self._initialize_run(graph)
        task_queue = asyncio.Queue()
        for node_id in run.get_nodes_in_state(NodeState.READY):
            await task_queue.put(node_id)
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        await task_queue.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        print("Graph execution finished.")
        return run.get_final_state()

    def _initialize_run(self, graph: Graph) -> 'GraphRun':
        try:
            return GraphRun(graph)
        except ValueError as e:
            raise ValueError(f"Graph has a cycle: {e}") from e

    async def _worker(self, name: str, run: 'GraphRun', queue: asyncio.Queue):
        """工作者协程，从队列中获取并处理节点。"""
        while True:
            try:
                node_id = await queue.get()
                print(f"[{name}] Picked up node: {node_id}")

                node = run.get_node(node_id)
                context = run.get_execution_context()
                
                run.set_node_state(node_id, NodeState.RUNNING)
                
                try:
                    output = await self._execute_node(node, context)
                    
                    # 检查返回的 output 是否是一个我们定义的错误结构
                    if isinstance(output, dict) and "error" in output:
                        # 这是 _execute_node 内部捕获并返回的错误（例如，管道失败）
                        print(f"[{name}] Node {node_id} FAILED (internally): {output['error']}")
                        run.set_node_result(node_id, output)
                        run.set_node_state(node_id, NodeState.FAILED)
                    else:
                        # 这是正常的成功执行
                        run.set_node_result(node_id, output)
                        run.set_node_state(node_id, NodeState.SUCCEEDED)
                        print(f"[{name}] Node {node_id} SUCCEEDED.")

                    # 无论成功或内部失败，都通知下游节点
                    self._process_subscribers(node_id, run, queue)

                except Exception as e:
                    # 这是 _execute_node 执行期间发生的意外异常
                    error_message = f"Unexpected error in worker for node {node_id}: {e}"
                    print(f"[{name}] Node {node_id} FAILED (unexpectedly): {error_message}")
                    run.set_node_result(node_id, {"error": error_message})
                    run.set_node_state(node_id, NodeState.FAILED)
                    
                    # 同样通知下游节点
                    self._process_subscribers(node_id, run, queue)

                finally:
                    queue.task_done()
            
            except asyncio.CancelledError:
                print(f"[{name}] shutting down.")
                break
    
    def _process_subscribers(self, completed_node_id: str, run: 'GraphRun', queue: asyncio.Queue):
        completed_node_state = run.get_node_state(completed_node_id)
        for sub_id in run.get_subscribers(completed_node_id):
            if run.get_node_state(sub_id) != NodeState.PENDING:
                continue
            if completed_node_state == NodeState.FAILED:
                run.set_node_state(sub_id, NodeState.SKIPPED)
                # 为下游节点记录跳过的原因
                run.set_node_result(sub_id, {
                    "status": "skipped",
                    "reason": f"Upstream failure of node {completed_node_id}."
                })
                self._process_subscribers(sub_id, run, queue)
                continue
            is_ready = True
            for dep_id in run.get_dependencies(sub_id):
                if run.get_node_state(dep_id) != NodeState.SUCCEEDED:
                    is_ready = False
                    break
            if is_ready:
                run.set_node_state(sub_id, NodeState.READY)
                queue.put_nowait(sub_id)


    async def _execute_node(self, node: GenericNode, context: ExecutionContext) -> Dict[str, Any]:
        """
        执行单个节点内的 Runtime 流水线。
        
        该方法实现了一个混合数据流模型：
        1. 转换流 (step_input): 每个 Runtime 的输出成为下一个的输入，实现覆盖式流水线。
        2. 增强流 (pipeline_state): 所有 Runtime 的输出被持续合并，为后续步骤提供完整的历史上下文。
        """
        node_id = node.id
        runtime_spec = node.data.get("runtime")
        
        if not runtime_spec:
            # 如果没有指定 runtime，可以认为该节点是一个纯粹的数据持有者
            return node.data

        runtime_names = [runtime_spec] if isinstance(runtime_spec, str) else runtime_spec

        # 1. 初始化两个数据流的起点
        #    - `pipeline_state` 用于累积和增强数据
        #    - `step_input` 用于在步骤间传递和转换数据
        pipeline_state = node.data.copy()
        step_input = node.data.copy()

        print(f"Executing node: {node_id} with runtime pipeline: {runtime_names}")
        
        for i, runtime_name in enumerate(runtime_names):
            print(f"  - Step {i+1}/{len(runtime_names)}: Running runtime '{runtime_name}'")
            try:
                # 从注册表获取一个新的 Runtime 实例
                runtime: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                # 调用 execute，传入两个数据流和全局上下文
                output = await runtime.execute(step_input, pipeline_state, context)
                
                # 检查输出是否为 None 或非字典，以增加健壮性
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Returned: {type(output).__name__}"
                    print(f"  - Error in pipeline: {error_message}")
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}

                # 2. 更新两个数据流
                #    - `step_input` 被完全覆盖，用于下一步
                step_input = output
                #    - `pipeline_state` 被合并更新，用于累积
                pipeline_state.update(output)

            except Exception as e:
                # 如果管道中任何一步失败，捕获异常并返回标准错误结构
                # import traceback; traceback.print_exc() # for debugging
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {e}"
                print(f"  - Error in pipeline: {error_message}")
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}

        # 3. 整个节点流水线成功完成后，返回最终的、最完整的累积状态
        print(f"Node {node_id} pipeline finished successfully.")
        return pipeline_state