# backend/core/engine.py
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
from backend.core.runtime import RuntimeInterface # 显式导入


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
        # 使用新的模型结构进行依赖解析
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
        if triggering_input is None: triggering_input = {}
        context = ExecutionContext.from_snapshot(initial_snapshot, {"trigger_input": triggering_input})
        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' graph not found.")
        
        final_node_states = await self._execute_graph(main_graph_def, context)

        next_snapshot = context.to_next_snapshot(final_node_states, triggering_input)
        print(f"Step complete. New snapshot {next_snapshot.id} created.")
        return next_snapshot

    async def _execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run = GraphRun(context, graph_def)
        task_queue = asyncio.Queue()

        # --- 新增逻辑：处理继承的输入 ---
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                # 将占位符节点的状态设置为 SUCCEEDED 并存储其结果
                # 即使 node_id 不在 run.node_map 中，这也能正常工作
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)

        # --- 修改后的逻辑：确定初始的 READY 节点 ---
        # 扫描所有 PENDING 节点，看它们的依赖是否已经满足（包括被注入的依赖）
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)

        # 将所有初始状态为 READY 的节点（无论是无依赖还是依赖已满足）放入队列
        for node_id in run.get_nodes_in_state(NodeState.READY):
            await task_queue.put(node_id)
        
        if task_queue.empty() and not any(s in (NodeState.SUCCEEDED, NodeState.RUNNING) for s in run.node_states.values()):
            # 如果队列为空且图中没有任何节点运行或成功，这可能意味着图是空的或无法启动
             if not run.node_map:
                 print("Graph is empty, finishing immediately.")
             else:
                 print("Warning: No nodes could be made ready to run in the graph.")
        
        workers = [asyncio.create_task(self._worker(f"worker-{i}", run, task_queue)) for i in range(self.num_workers)]
        
        await task_queue.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        
        # 返回所有已定义节点的最终状态
        final_states = {nid: run.get_node_result(nid) for nid in run.node_map if run.get_node_result(nid) is not None}
        return final_states


    async def _worker(self, name: str, run: 'GraphRun', queue: asyncio.Queue):
        while True:
            try:
                node_id = await queue.get()
                print(f"[{name}] Picked up node: {node_id}")
                node = run.get_node(node_id)
                context = run.get_execution_context()
                run.set_node_state(node_id, NodeState.RUNNING)
                
                try:
                    output = await self._execute_node(node, context)
                    if isinstance(output, dict) and "error" in output:
                        print(f"[{name}] Node {node_id} FAILED (internally): {output['error']}")
                        run.set_node_result(node_id, output)
                        run.set_node_state(node_id, NodeState.FAILED)
                    else:
                        run.set_node_result(node_id, output)
                        run.set_node_state(node_id, NodeState.SUCCEEDED)
                        print(f"[{name}] Node {node_id} SUCCEEDED.")
                    self._process_subscribers(node_id, run, queue)
                except Exception as e:
                    error_message = f"Unexpected error in worker for node {node_id}: {e}"
                    print(f"[{name}] Node {node_id} FAILED (unexpectedly): {error_message}")
                    run.set_node_result(node_id, {"error": error_message})
                    run.set_node_state(node_id, NodeState.FAILED)
                    self._process_subscribers(node_id, run, queue)
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                print(f"[{name}] shutting down.")
                break
    
    def _process_subscribers(self, completed_node_id: str, run: 'GraphRun', queue: asyncio.Queue):
        completed_node_state = run.get_node_state(completed_node_id)
        for sub_id in run.get_subscribers(completed_node_id):
            if run.get_node_state(sub_id) != NodeState.PENDING: continue
            if completed_node_state == NodeState.FAILED:
                run.set_node_state(sub_id, NodeState.SKIPPED)
                run.set_node_result(sub_id, {"status": "skipped", "reason": f"Upstream failure of node {completed_node_id}."})
                self._process_subscribers(sub_id, run, queue)
                continue
            is_ready = all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in run.get_dependencies(sub_id))
            if is_ready:
                run.set_node_state(sub_id, NodeState.READY)
                queue.put_nowait(sub_id)

    # --- THE CORE REFACTORED METHOD ---
    async def _execute_node(self, node: GenericNode, context: ExecutionContext) -> Dict[str, Any]:
        """
        【新】按顺序执行节点内的运行时指令，在每一步之前进行宏求值。
        """
        node_id = node.id
        print(f"Executing node: {node_id}")

        # pipeline_state 在指令间传递和累积
        pipeline_state: Dict[str, Any] = {}

        if not node.run:
            print(f"Node {node_id} has no run instructions, finishing.")
            return {}

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            print(f"  - Step {i+1}/{len(node.run)}: Running runtime '{runtime_name}'")
            
            try:
                # 1. 对当前指令的 config 进行宏求值
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                processed_config = await evaluate_data(instruction.config, eval_context)

                # 2. 获取运行时实例
                runtime: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                # 3. 执行运行时
                output = await runtime.execute(
                    config=processed_config,
                    pipeline_state=pipeline_state,
                    context=context,
                    node=node,
                    engine=self
                )
                
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Got: {type(output).__name__}"
                    print(f"  - Error in pipeline: {error_message}")
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}

                # 4. 更新管道状态，为下一个指令做准备
                pipeline_state.update(output)

            except Exception as e:
                import traceback
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {e}"
                print(f"  - Error in pipeline: {error_message}")
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}

        print(f"Node {node_id} pipeline finished successfully.")
        return pipeline_state