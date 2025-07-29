### models.py
```
# backend/models.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

# Edge模型保持不变
class Edge(BaseModel):
    source: str
    target: str

# 这是关键的重构：我们不再使用字面量类型 (Literal)
# 而是创建一个通用的节点模型
class GenericNode(BaseModel):
    id: str
    
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置，必须包含 'runtime' 字段来指定执行器"
    )

    @field_validator('data')
    @classmethod
    def check_runtime_exists(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if 'runtime' not in v:
            raise ValueError("Node data must contain a 'runtime' field.")
        
        runtime_value = v['runtime']
        if not (isinstance(runtime_value, str) or 
                (isinstance(runtime_value, list) and all(isinstance(item, str) for item in runtime_value))):
            raise ValueError("'runtime' must be a string or a list of strings.")
            
        return v

class Graph(BaseModel):
    nodes: List[GenericNode]
    edges: List[Edge]
```

### README.md
```

# Hevno Backend Engine

欢迎来到 Hevno 项目的后端引擎！这是一个高度可扩展、由配置驱动的图执行引擎，旨在为复杂的、多步骤的LLM应用提供动力。

## 核心设计哲学

本项目的构建基于一个核心哲学：**“拒绝类型爆炸，拥抱配置组合”**。

在许多工作流或节点编辑器系统中，功能的增加往往伴随着新节点类型（`If-Else Node`, `Loop Node`, `Sub-Flow Node` 等）的涌入。这种方式虽然初看直观，但长期来看会导致系统变得复杂、僵化，并增加用户的学习成本。

我们采取了截然不同的方法：

1.  **极简的节点结构**: 我们只有一个通用的节点模型 (`GenericNode`)。一个节点是“LLM调用”还是“代码执行”，不由其类型决定。

2.  **行为由运行时配置决定**: 节点是一个“变色龙”，其具体行为完全由其数据负载中的 `runtime` 字段指定。这意味着我们可以通过增加新的`runtime`实现来无限扩展功能，而无需修改或增加基础节点结构。

    *   **旧方式 (我们避免的)**:
        ```json
        {"type": "LLMNode", "prompt": "..."}
        {"type": "CodeNode", "code": "..."}
        ```

    *   **Hevno 的方式 (我们采用的)**:
        ```json
        {"type": "default", "data": {"runtime": "llm.default", "prompt": "..."}}
        {"type": "default", "data": {"runtime": "code.python", "code": "..."}}
        ```

3.  **元能力下沉为核心函数**: 像“修改流图”或“创建新节点”这样的系统级“元能力”，我们不将其实现为特殊的节点类型。相反，它们将被实现为可供任何运行时调用的内置核心函数。这使得系统的核心功能和用户自定义功能在结构上完全等价，极大地增强了统一性和灵活性。

这种设计使得 Hevno 不仅仅是一个应用，更是一个构建AI原生工作流的**框架**。

```

### main.py
```
# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 1. 导入新的模型和核心组件
from backend.models import Graph
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry

# 2. 导入并注册基础运行时
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime

# --- 初始化和插件加载 ---
def setup_application():
    app = FastAPI(
        title="Hevno Backend",
        description="The core execution engine for Hevno project.",
        version="0.1.0-refactored"
    )
    
    # 注册核心运行时
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("system.template", TemplateRuntime)
    runtime_registry.register("llm.default", LLMRuntime)

    # --- 这里是未来插件系统的入口 ---
    # def load_plugins():
    #     # 伪代码: 扫描 'plugins' 目录
    #     # for plugin_module in find_plugins():
    #     #     plugin_module.register(runtime_registry, function_registry, ...)
    # load_plugins()
    
    # CORS中间件
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
execution_engine = ExecutionEngine(registry=runtime_registry)

# --- API 端点 ---
@app.post("/api/graphs/execute")
async def execute_graph_endpoint(graph: Graph):
    try:
        result_context = await execution_engine.execute(graph)
        return result_context
    except ValueError as e:
        # 捕获已知的用户输入错误，例如环路
        raise HTTPException(status_code=400, detail=f"Invalid graph structure: {e}")
    except Exception as e:
        # 未预料到的服务器内部错误
        # 可以在这里添加日志记录
        # import logging; logging.exception("Graph execution failed")
        raise HTTPException(status_code=500, detail=f"An unexpected graph execution error occurred: {e}")
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on refactored architecture!"}
```

### core/templating.py
```
# backend/core/templating.py (最终正确版)
import jinja2
from typing import Any
from backend.core.runtime import ExecutionContext

# create_template_environment 不再需要，可以删除或简化为一个只创建env的函数
def get_jinja_env():
    return jinja2.Environment(
        enable_async=True,
        # 修复：使用 StrictUndefined，这样当变量不存在时会抛出 UndefinedError
        undefined=jinja2.StrictUndefined 
    )

async def render_template(template_str: str, context: ExecutionContext) -> str:
    """
    一个辅助函数，使用最新的上下文来渲染模板。
    """
    if '{{' not in template_str:
        return template_str
        
    env = get_jinja_env()
    template = env.from_string(template_str)
    
    # 动态构建完整的渲染上下文
    render_context = {
        "nodes": context.state,
        "vars": context.global_vars,
        "session": context.session_info,
        # 未来可以在这里注入函数
    }

    try:
        return await template.render_async(render_context)
    except Exception as e:
        raise IOError(f"Template rendering failed: {e}")
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

### core/__init__.py
```

```

### core/runtime.py
```
# backend/core/runtime.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field 
import asyncio
from datetime import datetime, timezone


class ExecutionContext(BaseModel):
    # 之前已有的
    state: Dict[str, Any] 
    graph: Any
    
    # --- 新增的全局变量 ---
    # 会话级的元数据
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,
    })
    
    # 全局变量存储，可以在图执行过程中被修改和读取
    global_vars: Dict[str, Any] = Field(default_factory=dict)

    # 我们之前构想的函数注册表
    function_registry: Dict[str, Callable] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True
    }

class RuntimeInterface(ABC):
    """定义所有运行时都必须遵守的接口 (使用抽象基类)"""
    @abstractmethod
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        - node_data: 节点自身的data字段。
        - context: 当前的执行上下文。
        - 返回值: 该节点的输出，将被存入全局状态。
        """
        pass
```

### core/engine.py
```
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


    async def _execute_node(self, node, context: ExecutionContext) -> Dict[str, Any]:
        """
        一个辅助方法，用于执行单个节点。
        现在它能正确捕获并处理管道中每一步的异常。
        """
        node_id = node.id
        runtime_spec = node.data.get("runtime")
        
        if not runtime_spec:
            return {"skipped": True}

        if isinstance(runtime_spec, str):
            runtime_names = [runtime_spec]
        else:
            runtime_names = runtime_spec

        pipeline_input = node.data
        final_output = {}

        print(f"Executing node: {node_id} with runtime pipeline: {runtime_names}")
        
        for i, runtime_name in enumerate(runtime_names):
            print(f"  - Step {i+1}/{len(runtime_names)}: Running runtime '{runtime_name}'")
            try:
                runtime = self.registry.get_runtime(runtime_name)
                
                # 它精确地包围了可能出错的 runtime.execute 调用
                current_step_input = {**pipeline_input, "node_data": node.data}
                output = await runtime.execute(current_step_input, context)
                
                pipeline_input = output
                final_output = output

            except Exception as e:
                # 如果管道中任何一步失败，捕获异常
                error_message = f"Failed at step {i+1} ('{runtime_name}'): {e}"
                print(f"  - Error in pipeline: {error_message}")
                # 返回一个标准的错误结构
                return {"error": error_message, "failed_step": i, "runtime": runtime_name}

        # 整个管道成功完成后，返回最后一个运行时的输出
        return final_output

```

### runtimes/__init__.py
```

```

### runtimes/base_runtimes.py
```
# backend/runtimes/base_runtimes.py
from backend.core.runtime import RuntimeInterface, ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点。它只关心自己的配置值。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 逻辑变得非常简单
        return {"output": node_data.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """通用的模板渲染运行时。它会在输入中查找 'template' 字段。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        template_str = node_data.get("template", "")
        if not template_str:
            raise ValueError("TemplateRuntime requires a 'template' string from its input.")
            
        rendered_string = await render_template(template_str, context)
        # 修复：只返回它生成的核心输出，而不是合并所有输入
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时。它会查找 'prompt' 或 'output' 字段作为输入。"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        prompt_template_str = node_data.get("prompt", node_data.get("output", ""))

        if not prompt_template_str:
            raise ValueError("LLMRuntime requires a 'prompt' or 'output' string from its input.")

        rendered_prompt = await render_template(prompt_template_str, context)
        
        await asyncio.sleep(0.1)
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        # 修复：同样，只返回LLM生成的核心数据
        return {"output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}
```
