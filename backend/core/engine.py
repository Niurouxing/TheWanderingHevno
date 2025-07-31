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
from backend.core.runtime import RuntimeInterface

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
        return next_snapshot

    async def _execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run = GraphRun(context, graph_def)
        task_queue = asyncio.Queue()

        if "global_write_lock" not in context.internal_vars:
            context.internal_vars["global_write_lock"] = asyncio.Lock()

        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)

        for node_id in list(run.node_map.keys()):
            if run.get_node_state(node_id) == NodeState.PENDING:
                dependencies = run.get_dependencies(node_id)
                if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                    run.set_node_state(node_id, NodeState.READY)

        for node_id in run.get_nodes_in_state(NodeState.READY):
            task_queue.put_nowait(node_id)

        if task_queue.empty() and not any(s == NodeState.SUCCEEDED for s in run.node_states.values()):
            return run.get_final_node_states()

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        await task_queue.join()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        final_states = {nid: run.get_node_result(nid) for nid in run.node_map if run.get_node_result(nid) is not None}
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
                output = await self._execute_node(node, context)
                if isinstance(output, dict) and "error" in output:
                    run.set_node_state(node_id, NodeState.FAILED)
                else:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, output)
            except Exception as e:
                error_message = f"Unexpected error in worker for node {node_id}: {type(e).__name__}: {e}"
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
        node_id = node.id
        pipeline_state: Dict[str, Any] = {}
        if not node.run:
            return {}
        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            try:
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                config_to_process = instruction.config.copy()
                using_template = None
                collect_template = None
                if runtime_name == "system.map":
                    using_template = config_to_process.pop('using', {})
                    collect_template = config_to_process.pop('collect', None)
                processed_config = await evaluate_data(config_to_process, eval_context)
                if runtime_name == "system.map":
                    processed_config['using'] = using_template
                    processed_config['collect'] = collect_template
                runtime: RuntimeInterface = self.registry.get_runtime(runtime_name)
                output = await runtime.execute(
                    config=processed_config,
                    pipeline_state=pipeline_state,
                    context=context,
                    node=node,
                    engine=self
                )
                if not isinstance(output, dict):
                    error_message = f"Runtime '{runtime_name}' did not return a dictionary. Got: {type(output).__name__}"
                    return {"error": error_message, "failed_step": i, "runtime": runtime_name}
                pipeline_state.update(output)
            except Exception as e:
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {type(e).__name__}: {e}"
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}
        return pipeline_state
