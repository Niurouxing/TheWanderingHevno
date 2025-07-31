### models.py
```
# backend/models.py 
from pydantic import BaseModel, Field, RootModel
from typing import List, Dict, Any

class RuntimeInstruction(BaseModel):
    """
    一个运行时指令，封装了运行时名称及其隔离的配置。
    这是节点执行逻辑的基本单元。
    """
    runtime: str
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="该运行时专属的、隔离的配置字典。"
    )

class GenericNode(BaseModel):
    """
    节点模型，现在以一个有序的运行时指令列表为核心。
    """
    id: str
    run: List[RuntimeInstruction] = Field(
        ...,
        description="定义节点执行逻辑的有序指令列表。"
    )

class GraphDefinition(BaseModel):
    """图定义，包含一个节点列表。"""
    nodes: List[GenericNode]

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    """
    整个配置文件的顶层模型。
    使用 RootModel，模型本身就是一个 `Dict[str, GraphDefinition]`。
    """
    
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        """验证器，确保存在一个 'main' 图作为入口点。"""
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v
```


### main.py
```
# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Dict, Any, List, Optional
from uuid import UUID

# 1. 导入新的模型
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, LLMRuntime, SetWorldVariableRuntime
from backend.runtimes.control_runtimes import ExecuteRuntime 
from backend.core.state_models import Sandbox, SnapshotStore, StateSnapshot

class CreateSandboxRequest(BaseModel):
    # 此处引用了新的 GraphCollection 模型，FastAPI 会自动使用新的验证规则
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None

def setup_application():
    app = FastAPI(
        title="Hevno Backend Engine",
        description="The core execution engine for Hevno project, supporting runtime-centric, sequential node execution.",
        version="0.3.0-runtime-centric"
    )
    
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("llm.default", LLMRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
    runtime_registry.register("system.execute", ExecuteRuntime)
    
    origins = ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app

app = setup_application()
sandbox_store: Dict[UUID, Sandbox] = {}
snapshot_store = SnapshotStore()
execution_engine = ExecutionEngine(registry=runtime_registry)

@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(request: CreateSandboxRequest, name: str):
    sandbox = Sandbox(name=name)
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        graph_collection=request.graph_collection,
        world_state=request.initial_state or {}
    )
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    return sandbox

@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(sandbox_id: UUID, user_input: Dict[str, Any] = Body(...)):
    sandbox = sandbox_store.get(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    latest_snapshot = sandbox.get_latest_snapshot(snapshot_store)
    if not latest_snapshot:
        raise HTTPException(status_code=409, detail="Sandbox has no initial state.")
    new_snapshot = await execution_engine.step(latest_snapshot, user_input)
    snapshot_store.save(new_snapshot)
    sandbox.head_snapshot_id = new_snapshot.id
    return new_snapshot

@app.get("/api/sandboxes/{sandbox_id}/history", response_model=List[StateSnapshot])
async def get_sandbox_history(sandbox_id: UUID):
    snapshots = snapshot_store.find_by_sandbox(sandbox_id)
    if not snapshots and not sandbox_store.get(sandbox_id):
        raise HTTPException(status_code=404, detail="Sandbox not found.")
    return snapshots

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(sandbox_id: UUID, snapshot_id: UUID):
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    sandbox.head_snapshot_id = snapshot_id
    sandbox_store[sandbox.id] = sandbox # 确保更新存储中的沙盒对象
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on runtime-centric architecture!"}

# 注意: `user_input` 在 `execute_sandbox_step` 中改用 Body(...) 以符合 FastAPI 的最佳实践
```

### core/registry.py
```
# backend/core/registry.py
from typing import Dict, Type
from backend.core.runtime import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        # 只存储类，不存储实例
        self._registry: Dict[str, Type[RuntimeInterface]] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._registry:
            print(f"Warning: Overwriting runtime registration for '{name}'.")
        self._registry[name] = runtime_class
        print(f"Runtime class '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime_class = self._registry.get(name)
        if runtime_class is None:
            raise ValueError(f"Runtime '{name}' not found.")
        
        # 总是返回一个新的实例
        return runtime_class()

# 全局单例保持不变
runtime_registry = RuntimeRegistry()
```

### core/evaluation.py
```
# backend/core/evaluation.py
import ast
import asyncio
import re
from typing import Any, Dict, List, Optional   
from functools import partial
# --- 1. 导入新的工具类 ---
from backend.core.utils import DotAccessibleDict

# 预编译宏的正则表达式，用于快速查找
MACRO_REGEX = re.compile(r"^{{\s*(.+)\s*}}$", re.DOTALL)

# --- 预置的、开箱即用的模块 ---
# 我们在这里定义它们，以便在构建上下文时注入
import random
import math
import datetime
import json
import re as re_module

PRE_IMPORTED_MODULES = {
    "random": random,
    "math": math,
    "datetime": datetime,
    "json": json,
    "re": re_module,
}


def build_evaluation_context(
    exec_context: 'ExecutionContext',
    pipe_vars: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    从 ExecutionContext 和可选的管道变量构建一个扁平的字典，用作宏的执行环境。
    """
    context = {
        **PRE_IMPORTED_MODULES,
        "world": DotAccessibleDict(exec_context.world_state),
        "nodes": DotAccessibleDict(exec_context.node_states),
        "run": DotAccessibleDict(exec_context.run_vars),
        "session": DotAccessibleDict(exec_context.session_info),
    }
    # 为了清晰和避免命名冲突，将管道变量放在 'pipe' 命名空间下
    if pipe_vars is not None:
        context['pipe'] = DotAccessibleDict(pipe_vars)
        
    return context

async def evaluate_expression(code_str: str, context: Dict[str, Any]) -> Any:
    """
    安全地执行一段 Python 代码字符串并返回结果。
    这是宏系统的执行核心。
    """
    # 使用 ast 来智能处理返回值
    # 1. 解析代码
    try:
        tree = ast.parse(code_str, mode='exec')
    except SyntaxError as e:
        raise ValueError(f"Macro syntax error: {e}\nCode: {code_str}")

    result_var = "_macro_result"
    
    # 2. 如果最后一条语句是表达式，将其结果赋值给 _macro_result
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        # 创建一个赋值节点
        assign_node = ast.Assign(
            targets=[ast.Name(id=result_var, ctx=ast.Store())],
            value=tree.body[-1].value
        )
        # 替换最后一个表达式节点
        tree.body[-1] = ast.fix_missing_locations(assign_node)

    # 3. 在非阻塞的执行器中运行同步的 exec
    loop = asyncio.get_running_loop()
    
    # exec 需要一个 globals 和一个 locals 字典
    local_scope = {}

    # partial 将函数和其参数打包，以便 run_in_executor 调用
    exec_func = partial(exec, compile(tree, filename="<macro>", mode="exec"), context, local_scope)
    
    await loop.run_in_executor(None, exec_func)
    
    # 4. 返回结果
    return local_scope.get(result_var)


async def evaluate_data(data: Any, eval_context: Dict[str, Any]) -> Any:
    """
    递归地遍历一个数据结构 (dict, list)，查找并执行所有宏。
    这是 `_execute_node` 将调用的主入口函数。
    """
    if isinstance(data, str):
        match = MACRO_REGEX.match(data)
        if match:
            code_to_run = match.group(1)
            # 发现宏，执行它并返回结果
            return await evaluate_expression(code_to_run, eval_context)
        # 不是宏，原样返回
        return data
        
    if isinstance(data, dict):
        # 异步地处理字典中的所有值
        # 注意：我们不处理 key，只处理 value
        keys = data.keys()
        values = [evaluate_data(v, eval_context) for v in data.values()]
        evaluated_values = await asyncio.gather(*values)
        return dict(zip(keys, evaluated_values))

    if isinstance(data, list):
        # 异步地处理列表中的所有项
        items = [evaluate_data(item, eval_context) for item in data]
        return await asyncio.gather(*items)

    # 对于其他类型（数字、布尔等），原样返回
    return data
```

### core/__init__.py
```

```

### core/types.py
```
# backend/core/types.py 
from __future__ import annotations
import json 
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone

from backend.core.state_models import StateSnapshot
from backend.models import GraphCollection

class ExecutionContext(BaseModel):
    initial_snapshot: StateSnapshot
    node_states: Dict[str, Any] = Field(default_factory=dict)
    world_state: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    function_registry: Dict[str, Callable] = Field(default_factory=dict)
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,
    })

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_snapshot(cls, snapshot: StateSnapshot, run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        return cls(
            initial_snapshot=snapshot,
            world_state=snapshot.world_state.copy(),
            run_vars=run_vars or {}
        )

    def to_next_snapshot(
        self,
        final_node_states: Dict[str, Any],
        triggering_input: Dict[str, Any]
    ) -> StateSnapshot:
        current_graphs = self.initial_snapshot.graph_collection
        if '__graph_collection__' in self.world_state:
            try:
                evolved_graph_value = self.world_state['__graph_collection__']
                if isinstance(evolved_graph_value, str):
                    evolved_graph_dict = json.loads(evolved_graph_value)
                else:
                    evolved_graph_dict = evolved_graph_value
                
                # 使用新的模型来验证
                evolved_graphs = GraphCollection.model_validate(evolved_graph_dict)
                current_graphs = evolved_graphs
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

        return StateSnapshot(
            sandbox_id=self.initial_snapshot.sandbox_id,
            graph_collection=current_graphs,
            world_state=self.world_state,
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )
        
ExecutionContext.model_rebuild()
```

### core/runtime.py
```
# backend/core/runtime.py 
from abc import ABC, abstractmethod
from typing import Dict, Any

class RuntimeInterface(ABC):
    """
    定义所有运行时都必须遵守的接口。
    """
    @abstractmethod
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        
        :param config: 经过宏求值后的、该运行时专属的配置字典。
        :param kwargs: 其他上下文信息，如 pipeline_state, context, engine。
        """
        pass
```

### core/engine.py
```
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

        if inherited_inputs:
            for node_id, result in inherited_inputs.items():
                if node_id not in run.node_map:
                    run.set_node_state(node_id, NodeState.SUCCEEDED)
                    run.set_node_result(node_id, result)

        task_queue = asyncio.Queue()
        for node_id in run.get_nodes_in_state(NodeState.READY):
            await task_queue.put(node_id)
        
        workers = [asyncio.create_task(self._worker(f"worker-{i}", run, task_queue)) for i in range(self.num_workers)]
        
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
                eval_context = build_evaluation_context(context)
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
```

### core/utils.py
```
# backend/core/utils.py

from typing import Any, Dict, List

class DotAccessibleDict:
    """
    一个【递归】代理类，它包装一个字典，并允许通过点符号进行属性访问。
    所有读取和写入操作都会直接作用于原始的底层字典。
    当访问一个值为字典的属性时，它会自动将该字典也包装成 DotAccessibleDict。
    """
    def __init__(self, data: Dict[str, Any]):
        object.__setattr__(self, "_data", data)

    @classmethod
    def _wrap(cls, value: Any) -> Any:
        """递归包装值。如果值是字典，包装它；如果是列表，递归包装其内容。"""
        if isinstance(value, dict):
            # 如果是字典，返回一个新的代理实例
            return cls(value)
        if isinstance(value, list):
            # 如果是列表，递归处理列表中的每一项
            return [cls._wrap(item) for item in value]
        # 其他类型原样返回
        return value

    def __getattr__(self, name: str) -> Any:
        """当访问 obj.key 时调用。"""
        try:
            # 获取原始值
            value = self._data[name]
            # 在返回值之前，递归地包装它！
            return self._wrap(value)
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        """当执行 obj.key = value 时调用。"""
        self._data[name] = value

    def __delattr__(self, name: str):
        """当执行 del obj.key 时调用。"""
        try:
            del self._data[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    # 保持辅助方法不变
    def __repr__(self) -> str:
        return f"DotAccessibleDict({self._data})"
    
    def __getitem__(self, key):
        return self._wrap(self._data[key])
    
    def __setitem__(self, key, value):
        self._data[key] = value
```

### core/state_models.py
```
# backend/core/state_models.py

from __future__ import annotations
from uuid import uuid4, UUID
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

# 导入这个文件所依赖的最基础模型
from backend.models import GraphCollection

# --- 所有相关的模型都住在这里 ---

class StateSnapshot(BaseModel):
    """
    一个不可变的快照，代表 Sandbox 在某个时间点的完整状态。
    """
    id: UUID = Field(default_factory=uuid4)
    sandbox_id: UUID
    graph_collection: GraphCollection
    world_state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_snapshot_id: Optional[UUID] = None
    triggering_input: Dict[str, Any] = Field(default_factory=dict)
    run_output: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(frozen=True)

class Sandbox(BaseModel):
    """
    一个交互式模拟环境的容器。
    它管理着一系列的状态快照。
    """
    id: UUID = Field(default_factory=uuid4)
    name: str
    head_snapshot_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_latest_snapshot(self, store: SnapshotStore) -> Optional[StateSnapshot]:
        # 现在 SnapshotStore 和 StateSnapshot 都在同一个作用域，类型提示完美工作
        if self.head_snapshot_id:
            return store.get(self.head_snapshot_id)
        return None

class SnapshotStore:
    """一个简单的内存快照存储。"""
    def __init__(self):
        self._store: Dict[UUID, StateSnapshot] = {}

    def save(self, snapshot: StateSnapshot):
        if snapshot.id in self._store:
            raise ValueError(f"Snapshot with id {snapshot.id} already exists.")
        self._store[snapshot.id] = snapshot

    def get(self, snapshot_id: UUID) -> Optional[StateSnapshot]:
        return self._store.get(snapshot_id)

    def find_by_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        return [s for s in self._store.values() if s.sandbox_id == sandbox_id]

    def clear(self):
        self._store = {}

# --- 在文件末尾重建所有模型 ---
# 这确保了 Pydantic 能够正确处理所有内部引用和向前引用
StateSnapshot.model_rebuild()
Sandbox.model_rebuild()
```

### core/dependency_parser.py
```
# backend/core/dependency_parser.py 
import re
from typing import Set, Dict, Any, List

# 正则表达式，用于匹配 {{...}} 宏内部的 `nodes.node_id` 模式
NODE_DEP_REGEX = re.compile(r'nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    """从单个字符串中提取所有节点依赖。"""
    if not isinstance(s, str):
        return set()
    # 仅在检测到宏标记时才进行解析，以提高效率并避免误报
    if '{{' in s and '}}' in s and 'nodes.' in s:
        return set(NODE_DEP_REGEX.findall(s))
    return set()

def extract_dependencies_from_value(value: Any) -> Set[str]:
    """递归地从任何值（字符串、列表、字典）中提取依赖。"""
    deps = set()
    if isinstance(value, str):
        deps.update(extract_dependencies_from_string(value))
    elif isinstance(value, list):
        for item in value:
            deps.update(extract_dependencies_from_value(item))
    elif isinstance(value, dict):
        for k, v in value.items():
            deps.update(extract_dependencies_from_value(k))
            deps.update(extract_dependencies_from_value(v))
    return deps

def build_dependency_graph(nodes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    根据节点列表自动构建依赖图。
    新版本从节点的 `run` 指令列表中提取依赖。
    """
    dependency_map: Dict[str, Set[str]] = {}
    node_ids = {node['id'] for node in nodes}

    for node in nodes:
        node_id = node['id']
        all_dependencies = set()

        # 遍历节点 `run` 列表中的每个指令
        for instruction in node.get('run', []):
            instruction_config = instruction.get('config', {})
            dependencies = extract_dependencies_from_value(instruction_config)
            all_dependencies.update(dependencies)
        
        # 过滤掉不存在的节点ID，这可能是子图的输入占位符
        valid_dependencies = {dep for dep in all_dependencies if dep in node_ids}
        dependency_map[node_id] = valid_dependencies
    
    return dependency_map
```

### runtimes/__init__.py
```

```

### runtimes/base_runtimes.py
```
# backend/runtimes/base_runtimes.py
import asyncio 
from backend.core.runtime import RuntimeInterface
from backend.core.types import ExecutionContext
from typing import Dict, Any

class InputRuntime(RuntimeInterface):
    """从 config 中获取 'value'。"""
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return {"output": config.get("value", "")}

class LLMRuntime(RuntimeInterface):
    """从自己的 config 中获取已经渲染好的 prompt。"""
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        rendered_prompt = config.get("prompt")

        # 也可以从管道状态中获取输入，以实现链式调用
        if not rendered_prompt:
            pipeline_state = kwargs.get("pipeline_state", {})
            rendered_prompt = pipeline_state.get("output", "")
        
        if not rendered_prompt:
            raise ValueError("LLMRuntime requires a 'prompt' in its config or an 'output' from the previous step.")

        # 模拟 LLM API 调用延迟
        await asyncio.sleep(0.1)
        
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}

class SetWorldVariableRuntime(RuntimeInterface):
    """从 config 中获取变量名和值，并设置一个持久化的世界变量。"""
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        context: ExecutionContext = kwargs.get("context")
        variable_name = config.get("variable_name")
        value_to_set = config.get("value")

        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name' in its config.")
        
        # 修改的是可变的 ExecutionContext.world_state
        context.world_state[variable_name] = value_to_set
        
        # 这个运行时通常没有自己的输出，只是产生副作用
        return {}
```

### runtimes/control_runtimes.py
```
# backend/runtimes/control_runtimes.py
from backend.core.runtime import RuntimeInterface
from backend.core.evaluation import evaluate_expression, build_evaluation_context
from typing import Dict, Any

class ExecuteRuntime(RuntimeInterface):
    """
    一个特殊的运行时，用于二次执行代码。
    它接收一个 'code' 字段，并对其内容进行求值。
    """
    async def execute(self, config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        context = kwargs.get("context")
        code_to_execute = config.get("code")

        if not isinstance(code_to_execute, str):
            return {"output": code_to_execute}

        # 构建当前的执行上下文
        eval_context = build_evaluation_context(context)

        # 进行二次求值
        result = await evaluate_expression(code_to_execute, eval_context)

        return {"output": result}

# 未来，system.map 和 system.call 也将放在这里
```
