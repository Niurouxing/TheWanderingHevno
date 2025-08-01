# backend/core/engine.py
import asyncio
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict

from backend.models import GraphCollection, GraphDefinition, GenericNode
from backend.core.dependency_parser import build_dependency_graph
from backend.core.registry import RuntimeRegistry
from backend.core.evaluation import build_evaluation_context, evaluate_data
from backend.core.types import ExecutionContext 
from backend.core.interfaces import RuntimeInterface, SubGraphRunner

class NodeState(Enum):
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    SKIPPED = auto()

class GraphRun:
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
        return self.dependencies.get(node_id, set())
    def get_subscribers(self, node_id: str) -> Set[str]:
        return self.subscribers.get(node_id, set())
    def get_execution_context(self) -> ExecutionContext:
        return self.context
    def get_final_node_states(self) -> Dict[str, Any]:
        return self.context.node_states

# ExecutionEngine 现在实现了 SubGraphRunner 接口
class ExecutionEngine(SubGraphRunner):
    def __init__(self, registry: RuntimeRegistry, num_workers: int = 5):
        self.registry = registry
        self.num_workers = num_workers

    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        if triggering_input is None: triggering_input = {}
        # --- 使用新的工厂方法创建主上下文 ---
        context = ExecutionContext.create_for_main_run(initial_snapshot, {"trigger_input": triggering_input})
        
        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' graph not found.")
        
        final_node_states = await self._internal_execute_graph(main_graph_def, context)
        next_snapshot = context.to_next_snapshot(final_node_states, triggering_input)
        return next_snapshot

    # --- 实现 SubGraphRunner 接口 ---
    async def execute_graph(
        self,
        graph_name: str,
        # 注意：这里接收的是一个 ExecutionContext，但我们将用它来创建子上下文
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """这是暴露给运行时的公共接口。"""
        graph_collection = parent_context.initial_snapshot.graph_collection.root
        graph_def = graph_collection.get(graph_name)
        if not graph_def:
            raise ValueError(f"Graph '{graph_name}' not found.")
        
        # --- 【关键】为子图运行创建自己的上下文 ---
        # 它会共享 world_state 和锁，但有自己的 node_states
        sub_run_context = ExecutionContext.create_for_sub_run(parent_context)

        return await self._internal_execute_graph(
            graph_def=graph_def,
            context=sub_run_context, # <-- 使用新的子上下文
            inherited_inputs=inherited_inputs
        )

    async def _internal_execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        内部核心调度器，用于执行一个图。
        
        :param graph_def: 要执行的图的 Pydantic 模型。
        :param context: 本次图执行的上下文（包含共享状态的引用和私有的 node_states）。
        :param inherited_inputs: (可选) 从父图（如 system.call 或 system.map）注入的预计算结果。
                                  这些被当作是已经“成功”的虚拟节点。
        :return: 一个字典，包含图中所有成功执行的节点的最终输出。
        """
        
        # --- 1. 初始化运行状态 ---
        # 创建一个 GraphRun 实例来管理这次运行的所有动态信息。
        # 这样可以将状态管理的复杂性从主函数中分离出去。
        run = GraphRun(context=context, graph_def=graph_def)

        # 创建一个异步任务队列，用于存放“准备就绪”可以执行的节点。
        task_queue = asyncio.Queue()
        
        # --- 2. 处理继承的输入 (用于子图) ---
        # 如果这是由 `call` 或 `map` 启动的子图，它可能会有 `inherited_inputs`。
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                # 我们将这些注入的输入视为已经成功完成的“占位符”节点。
                # 尽管这些节点ID可能不在当前图的 `node_map` 中，我们仍然设置它们的状态和结果。
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)
        
        # --- 3. 确定初始的可执行节点 ---
        # 再次检查所有“待定”节点，看它们的依赖是否已经满足（可能因为继承的输入）。
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            # all() 在空集合上返回 True，这正是我们想要的。
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)
        
        # 将所有初始“准备就绪”的节点放入任务队列。
        for node_id in run.get_nodes_in_state(NodeState.READY):
            task_queue.put_nowait(node_id)

        # --- 4. 检查是否无事可做 ---
        # 如果队列是空的，并且没有任何节点是“成功”状态（意味着没有继承的输入），
        # 那么这个图从一开始就无法执行。直接返回空结果。
        if task_queue.empty() and not any(s == NodeState.SUCCEEDED for s in run.node_states.values()):
            print(f"Warning: Graph '{graph_def.nodes[0].id if graph_def.nodes else 'empty'}' has no runnable starting nodes.")
            return {}

        # --- 5. 启动工作者 (Worker) 并执行 ---
        # 创建一组并发的工作者任务，它们将从队列中获取并执行节点。
        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        
        # 等待队列中的所有任务都被处理完毕。
        # `task_queue.join()` 会阻塞，直到每个 `put()` 都有一个对应的 `task_done()`。
        await task_queue.join()

        # --- 6. 清理并返回结果 ---
        # 一旦所有任务完成，我们就不再需要工作者了。取消它们以释放资源。
        for w in workers:
            w.cancel()
        
        # 等待所有取消操作完成。
        await asyncio.gather(*workers, return_exceptions=True)
        
        # 从上下文中收集所有被标记为有结果的节点的输出，并返回。
        # 这里的 `run.get_node_result(nid) is not None` 也可以用于过滤掉未执行或失败的节点。
        final_states = {
            nid: run.get_node_result(nid)
            for nid, n in run.node_map.items()
            if run.get_node_result(nid) is not None
        }
        return final_states

    async def _worker(self, name: str, run: 'GraphRun', queue: asyncio.Queue):
        while True:
            try:
                node_id = await queue.get()
            except asyncio.CancelledError:
                break

            run.set_node_state(node_id, NodeState.RUNNING)
            try:
                node = run.get_node(node_id)
                context = run.get_execution_context()
                # --- 将 _execute_node 的调用也包在 try...except 中 ---
                # 这样即使 _execute_node 内部的宏预处理失败，也能捕获
                output = await self._execute_node(node, context)
                if isinstance(output, dict) and "error" in output:
                    run.set_node_state(node_id, NodeState.FAILED)
                else:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, output)
            except Exception as e:
                # 这个捕获块现在变得更重要
                error_message = f"Worker-level error for node {node_id}: {type(e).__name__}: {e}"
                import traceback
                traceback.print_exc() # 打印完整的堆栈以供调试
                run.set_node_state(node_id, NodeState.FAILED)
                run.set_node_result(node_id, {"error": error_message})
            self._process_subscribers(node_id, run, queue)
            queue.task_done()

    def _process_subscribers(self, completed_node_id: str, run: 'GraphRun', queue: asyncio.Queue):
        completed_node_state = run.get_node_state(completed_node_id)
        for sub_id in run.get_subscribers(completed_node_id):
            if run.get_node_state(sub_id) != NodeState.PENDING:
                continue
            if completed_node_state == NodeState.FAILED:
                run.set_node_state(sub_id, NodeState.SKIPPED)
                run.set_node_result(sub_id, {"status": "skipped", "reason": f"Upstream failure of node {completed_node_id}."})
                self._process_subscribers(sub_id, run, queue)
                continue
            dependencies = run.get_dependencies(sub_id)
            is_ready = all(
                (dep_id not in run.node_map) or (run.get_node_state(dep_id) == NodeState.SUCCEEDED)
                for dep_id in dependencies
            )
            if is_ready:
                run.set_node_state(sub_id, NodeState.READY)
                queue.put_nowait(sub_id)

    async def _execute_node(self, node: GenericNode, context: ExecutionContext) -> Dict[str, Any]:
        pipeline_state: Dict[str, Any] = {}
        if not node.run: return {}
        
        # 从共享上下文中获取锁
        lock = context.shared.global_write_lock

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            try:
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                
                config_to_process = instruction.config.copy()
                runtime_instance: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                templates = {}
                template_fields = getattr(runtime_instance, 'template_fields', [])
                for field in template_fields:
                    if field in config_to_process:
                        templates[field] = config_to_process.pop(field)

                # --- 传递锁给求值函数 ---
                processed_config = await evaluate_data(config_to_process, eval_context, lock)

                if templates:
                    processed_config.update(templates)

                # --- 传递 self 作为 SubGraphRunner, context 作为上下文 ---
                output = await runtime_instance.execute(
                    config=processed_config,
                    context=context,
                    subgraph_runner=self,
                    pipeline_state=pipeline_state
                )
                
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Got: {type(output).__name__}"
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}
                pipeline_state.update(output)
            except Exception as e:
                # 打印详细的错误信息以便调试
                import traceback
                print(f"Error in node {node_id}, step {i} ({runtime_name}): {type(e).__name__}: {e}")
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {type(e).__name__}: {e}"
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}
        return pipeline_state