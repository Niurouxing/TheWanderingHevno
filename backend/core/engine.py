import asyncio
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict

# 导入新的模型和依赖解析器
from backend.models import GraphCollection, GraphDefinition, GenericNode
from backend.core.dependency_parser import build_dependency_graph
from backend.core.registry import RuntimeRegistry
from backend.core.evaluation import build_evaluation_context, evaluate_data
from backend.core.types import ExecutionContext


class NodeState(Enum):
    """定义节点在执行过程中的所有可能状态。"""
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    SKIPPED = auto()

class GraphRun:
    """管理一次图执行的状态，现在支持任意 GraphDefinition。"""
    def __init__(self, context: ExecutionContext, graph_def: GraphDefinition):
        self.context = context
        self.graph_def = graph_def
        if not self.graph_def:
            raise ValueError("GraphRun must be initialized with a valid GraphDefinition.")
        self.node_map: Dict[str, GenericNode] = {n.id: n for n in self.graph_def.nodes}
        self.node_states: Dict[str, NodeState] = {}
        self.dependencies: Dict[str, Set[str]] = build_dependency_graph(
            [node.model_dump() for node in self.graph_def.nodes]
        )
        self.subscribers: Dict[str, Set[str]] = self._build_subscribers()
        self._detect_cycles()
        self._initialize_node_states()

    def _build_subscribers(self) -> Dict[str, Set[str]]:
        subscribers = defaultdict(set)
        for node_id, deps in self.dependencies.items():
            for dep_id in deps:
                subscribers[dep_id].add(node_id)
        return subscribers

    def _detect_cycles(self):
        path = set()
        visited = set()
        def visit(node_id):
            path.add(node_id)
            visited.add(node_id)
            for neighbour in self.dependencies.get(node_id, set()):
                if neighbour in path:
                    raise ValueError(f"Cycle detected involving node {neighbour}")
                if neighbour not in visited:
                    visit(neighbour)
            path.remove(node_id)
        for node_id in self.node_map:
            if node_id not in visited:
                visit(node_id)

    def _initialize_node_states(self):
        for node_id in self.node_map:
            if not self.dependencies.get(node_id):
                self.node_states[node_id] = NodeState.READY
            else:
                self.node_states[node_id] = NodeState.PENDING

    def get_node(self, node_id: str) -> GenericNode:
        return self.node_map[node_id]
    def get_node_state(self, node_id: str) -> NodeState:
        return self.node_states.get(node_id)
    def set_node_state(self, node_id: str, state: NodeState):
        self.node_states[node_id] = state
    def get_node_result(self, node_id: str) -> Dict[str, Any]:
        return self.context.node_states.get(node_id)
    def set_node_result(self, node_id: str, result: Dict[str, Any]):
        self.context.node_states[node_id] = result
    def get_nodes_in_state(self, state: NodeState) -> List[str]:
        return [nid for nid, s in self.node_states.items() if s == state]
    def get_dependencies(self, node_id: str) -> Set[str]:
        return self.dependencies[node_id]
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers[node_id]
    def get_execution_context(self) -> ExecutionContext:
        return self.context
    def get_final_node_states(self) -> Dict[str, Any]:
        return self.context.node_states


class ExecutionEngine:
    def __init__(self, registry: RuntimeRegistry, num_workers: int = 5):
        self.registry = registry
        self.num_workers = num_workers

    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        """
        公开的入口点：执行一个完整的步骤，从一个快照到下一个。
        职责：创建顶层执行上下文，调用核心图执行逻辑。
        """
        if triggering_input is None:
            triggering_input = {}
        
        # 1. 创建顶层上下文
        context = ExecutionContext.from_snapshot(initial_snapshot, {"trigger_input": triggering_input})
        
        # 2. 获取入口图
        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def:
            raise ValueError("'main' graph not found in the initial snapshot.")

        # 3. 调用可重入的图执行器
        final_node_states = await self._execute_graph(main_graph_def, context)

        # 4. 创建下一个快照
        next_snapshot = context.to_next_snapshot(
            final_node_states=final_node_states,
            triggering_input=triggering_input
        )
        print(f"Step complete. New snapshot {next_snapshot.id} created.")
        return next_snapshot

    async def _execute_graph(
        self, 
        graph_def: GraphDefinition, 
        context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        核心的、可重入的图执行逻辑。
        它可以被 step() 调用，也可以被 map/call 运行时递归调用。

        :param graph_def: 要执行的图的定义。
        :param context: 共享的、可变的执行上下文。
        :param inherited_inputs: 从父图（例如 map/call 节点）注入的虚拟节点结果。
        :return: 此图执行完毕后所有节点的状态字典。
        """
        run = GraphRun(context, graph_def)

        # 这是实现 "输入占位符" 的关键！
        # 在图开始执行前，将继承的输入作为已成功的虚拟节点注入状态。
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                # 假设这些虚拟节点都是成功的
                run.set_node_result(node_id, result)
                # 注意：我们不需要在 GraphRun 的 node_states 中设置它们的状态，
                # 因为它们不是真正的待执行节点。依赖它们
                # 的节点在检查依赖状态时，只会检查 context.node_states 中是否有结果。
                # 修正：为了让依赖检查更严谨，我们需要让下游节点认为占位符已经“成功”。
                # 一个简单的策略是直接注入结果，并在依赖检查时只关心结果是否存在。
                # 让我们检查一下 _process_subscribers 的逻辑...
                # if run.get_node_state(dep_id) != NodeState.SUCCEEDED:
                # 啊哈，它确实检查 SUCCEEDED 状态。所以我们需要一个更好的策略。

                # --- 更好的策略 ---
                # 我们不在 GraphRun 中伪造状态，而是在 context 中预填充结果。
                # 依赖检查逻辑需要稍微调整，或者我们可以把占位符也加入到 node_map 和 node_states 中。
                # 最干净的方式是：在创建 GraphRun 时，就告诉它哪些是输入占位符。
                # 但为了不改动太多，让我们采用一个简单策略：
                # 在 `_process_subscribers` 中，如果一个依赖 `dep_id` 不在 `run.node_states` 中，
                # 但在 `run.context.node_states` 中有结果，就认为它是成功的。
                # 当前的实现不完全支持，所以我们先用注入结果的方式，后续 MapRuntime 再看如何处理。
                # 最简单的，还是在 GraphRun 中处理：
                if node_id not in run.node_map: # 确保它是个真正的占位符
                    run.set_node_state(node_id, NodeState.SUCCEEDED)
                    run.set_node_result(node_id, result)

        
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
        
        # 返回此子图执行的最终节点状态
        # 这里需要注意：我们应该只返回此 graph_def 中定义的节点的结果
        final_states = {
            node_id: run.get_node_result(node_id)
            for node_id in run.node_map
            if run.get_node_result(node_id) is not None
        }
        return final_states

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


    async def _execute_node(self, node: GenericNode, context: ExecutionContext):
        # 1. 初始宏预处理 (可选但推荐)
        #    只处理那些不依赖管道内部状态的、静态的宏。
        #    或者，我们可以完全放弃初始预处理，将所有求值都推迟到步骤中。
        #    为了简单起见，我们假设有一个初始的 `step_input`，它就是原始的 node.data。
        
        initial_data = node.data.copy()
        runtime_names = initial_data.pop("runtime", [])
        if not isinstance(runtime_names, list): runtime_names = [runtime_names]

        # 2. 初始化管道变量 (pipe)
        #    它的初始状态可以包含节点 data 中除了 runtime 自身以外的所有静态值。
        pipe_vars = initial_data.copy()

        # 3. 按顺序迭代运行时管道
        for runtime_name in runtime_names:
            runtime = self.registry.get_runtime(runtime_name)
            
            # 4. 【核心变更】步骤级宏求值
            #    a. 构建当前步骤的求值上下文，包含最新的 world, nodes, run, session, 和【可变的 pipe】
            current_eval_context = build_evaluation_context(context, pipe_vars)

            #    b. runtime 可以声明它需要哪些参数，引擎只对这些参数进行求值。
            #       或者一个更简单的实现：对整个 pipe_vars 进行一次宏求值。
            #       我们采用后者，它更通用。
            evaluated_step_input = await evaluate_data(pipe_vars, current_eval_context)
            
            # 5. 执行当前步骤的 runtime
            runtime_output = await runtime.execute(
                step_input=evaluated_step_input,  # runtime 接收到的是当前步骤计算好的输入
                context=context  # 全局上下文依然可用
            )

            # 6. 更新管道变量
            #    将当前 runtime 的输出合并到 pipe_vars 中，供下一步使用。
            if isinstance(runtime_output, dict):
                pipe_vars.update(runtime_output)

        # 7. 返回最终的管道状态作为节点结果
        return pipe_vars