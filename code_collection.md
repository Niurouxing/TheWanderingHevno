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
from backend.core.executor import GraphExecutor
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
graph_executor = GraphExecutor(registry=runtime_registry)

# --- API 端点 ---
@app.post("/api/graphs/execute")
async def execute_graph_endpoint(graph: Graph):
    try:
        result_context = await graph_executor.execute(graph)
        return result_context
    except Exception as e:
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
        # 存储类或实例
        self._registry: Dict[str, Union[Type[RuntimeInterface], RuntimeInterface]] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._registry:
            print(f"Warning: Overwriting runtime registration for '{name}'.")
        # 只存储类，不实例化
        self._registry[name] = runtime_class
        print(f"Runtime class '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        entry = self._registry.get(name)
        if entry is None:
            raise ValueError(f"Runtime '{name}' not found.")

        # 如果存储的是类，则实例化并替换它
        if isinstance(entry, type):
            print(f"Instantiating runtime '{name}' for the first time.")
            instance = entry()
            self._registry[name] = instance
            return instance
        
        # 否则，直接返回已有的实例
        return entry

# 创建一个全局单例
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

### core/executor.py
```
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
