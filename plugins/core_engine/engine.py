# plugins/core_engine/engine.py 

import asyncio
import logging
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict
import traceback

from backend.core.contracts import (
    GraphCollection, GraphDefinition, GenericNode, Container,
    ExecutionContext,
    EngineStepStartContext, EngineStepEndContext,
    BeforeConfigEvaluationContext, AfterMacroEvaluationContext,
    NodeExecutionStartContext, NodeExecutionSuccessContext, NodeExecutionErrorContext,
    HookManager
)
from .dependency_parser import build_dependency_graph_async
from .registry import RuntimeRegistry
from .evaluation import build_evaluation_context, evaluate_data
from .state import (
    create_main_execution_context, 
    create_sub_execution_context, 
    create_next_snapshot
)
from .interfaces import RuntimeInterface, SubGraphRunner

logger = logging.getLogger(__name__)

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
        self.dependencies: Dict[str, Set[str]] = {}
        self.subscribers: Dict[str, Set[str]] = {}

    @classmethod
    async def create(cls, context: ExecutionContext, graph_def: GraphDefinition) -> "GraphRun":
        run = cls(context, graph_def)
        run.dependencies = await build_dependency_graph_async(
            [node.model_dump() for node in run.graph_def.nodes],
            context.hook_manager
        )
        run.subscribers = run._build_subscribers()
        run._detect_cycles()
        run._initialize_node_states()
        return run

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

class ExecutionEngine(SubGraphRunner):
    def __init__(
        self,
        registry: RuntimeRegistry,
        container: Container,
        hook_manager: HookManager,
        num_workers: int = 5
    ):
        self.registry = registry
        self.container = container
        self.hook_manager = hook_manager
        self.num_workers = num_workers
        
    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        if triggering_input is None: triggering_input = {}
        
        await self.hook_manager.trigger(
            "engine_step_start",
            context=EngineStepStartContext(
                initial_snapshot=initial_snapshot,
                triggering_input=triggering_input
            )
        )
        
        context = create_main_execution_context(
            snapshot=initial_snapshot,
            container=self.container,
            run_vars={"triggering_input": triggering_input},
            hook_manager=self.hook_manager
        )

        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def: raise ValueError("'main' graph not found.")
        
        final_node_states = await self._internal_execute_graph(main_graph_def, context)
        
        next_snapshot = await create_next_snapshot(
            context=context, 
            final_node_states=final_node_states, 
            triggering_input=triggering_input
        )

        await self.hook_manager.trigger(
            "engine_step_end",
            context=EngineStepEndContext(final_snapshot=next_snapshot)
        )

        return next_snapshot

    async def execute_graph(
        self,
        graph_name: str,
        parent_context: ExecutionContext,
        inherited_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        graph_collection = parent_context.initial_snapshot.graph_collection.root
        graph_def = graph_collection.get(graph_name)
        if not graph_def:
            raise ValueError(f"Graph '{graph_name}' not found.")
        
        sub_run_context = create_sub_execution_context(parent_context)

        return await self._internal_execute_graph(
            graph_def=graph_def,
            context=sub_run_context,
            inherited_inputs=inherited_inputs
        )

    async def _internal_execute_graph(self, graph_def: GraphDefinition, context: ExecutionContext, inherited_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run = await GraphRun.create(context=context, graph_def=graph_def)
        task_queue = asyncio.Queue()
        
        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                run.set_node_state(node_id, NodeState.SUCCEEDED)
                run.set_node_result(node_id, result)
        
        for node_id in run.get_nodes_in_state(NodeState.PENDING):
            dependencies = run.get_dependencies(node_id)
            if all(run.get_node_state(dep_id) == NodeState.SUCCEEDED for dep_id in dependencies):
                run.set_node_state(node_id, NodeState.READY)
        
        for node_id in run.get_nodes_in_state(NodeState.READY):
            task_queue.put_nowait(node_id)

        if task_queue.empty() and not any(s == NodeState.SUCCEEDED for s in run.node_states.values()):
            return {}

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}", run, task_queue))
            for i in range(self.num_workers)
        ]
        
        await task_queue.join()

        for w in workers:
            w.cancel()
        
        await asyncio.gather(*workers, return_exceptions=True)
        
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

                await self.hook_manager.trigger(
                    "node_execution_start",
                    context=NodeExecutionStartContext(node=node, execution_context=context)
                )
                output = await self._execute_node(node, context)
                if isinstance(output, dict) and "error" in output:
                    run.set_node_state(node_id, NodeState.FAILED)

                    await self.hook_manager.trigger(
                        "node_execution_error",
                        context=NodeExecutionErrorContext(
                            node=node,
                            execution_context=context,
                            exception=ValueError(output["error"])
                        )
                    )
                else:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)

                    await self.hook_manager.trigger(
                        "node_execution_success",
                        context=NodeExecutionSuccessContext(
                            node=node,
                            execution_context=context,
                            result=output
                        )
                    )
                run.set_node_result(node_id, output)
            except Exception as e:
                error_message = f"Worker-level error for node {node_id}: {type(e).__name__}: {e}"
                import traceback
                traceback.print_exc()
                run.set_node_state(node_id, NodeState.FAILED)
                run.set_node_result(node_id, {"error": error_message})

                await self.hook_manager.trigger(
                    "node_execution_error",
                    context=NodeExecutionErrorContext(
                        node=node,
                        execution_context=context,
                        exception=e
                    )
                )
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
        
        lock = context.shared.global_write_lock

        for i, instruction in enumerate(node.run):
            runtime_name = instruction.runtime
            try:
                eval_context = build_evaluation_context(context, pipe_vars=pipeline_state)
                
                config_to_process = instruction.config.copy()

                config_to_process = await self.hook_manager.filter(
                    "before_config_evaluation",
                    config_to_process,
                    context=BeforeConfigEvaluationContext(
                        node=node,
                        execution_context=context,
                        instruction_config=config_to_process
                    )
                )

                runtime_instance: RuntimeInterface = self.registry.get_runtime(runtime_name)
                
                templates = {}
                template_fields = getattr(runtime_instance, 'template_fields', [])
                for field in template_fields:
                    if field in config_to_process:
                        templates[field] = config_to_process.pop(field)

                processed_config = await evaluate_data(config_to_process, eval_context, lock)

                processed_config = await self.hook_manager.filter(
                    "after_macro_evaluation",
                    processed_config,
                    context=AfterMacroEvaluationContext(
                        node=node,
                        execution_context=context,
                        evaluated_config=processed_config
                    )
                )

                if templates:
                    processed_config.update(templates)

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
                import traceback
                traceback.print_exc()
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {type(e).__name__}: {e}"
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}
        return pipeline_state

def get_engine(request: Request) -> ExecutionEngine:
    return request.app.state.engine
