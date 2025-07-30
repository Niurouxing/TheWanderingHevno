### models.py
```
# backend/models.py
from pydantic import BaseModel, Field, field_validator, RootModel
from typing import List, Dict, Any

class GenericNode(BaseModel):
    id: str
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置，必须包含 'runtime' 字段来指定执行器"
    )

    @field_validator('data')
    @classmethod
    def check_runtime_exists(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # 这个验证器保持不变，依然很好用
        if 'runtime' not in v:
            raise ValueError("Node data must contain a 'runtime' field.")
        runtime_value = v['runtime']
        if not (isinstance(runtime_value, str) or 
                (isinstance(runtime_value, list) and all(isinstance(item, str) for item in runtime_value))):
            raise ValueError("'runtime' must be a string or a list of strings.")
        return v

class GraphDefinition(BaseModel):

    nodes: List[GenericNode]

class GraphCollection(RootModel[Dict[str, GraphDefinition]]):
    """
    整个配置文件的顶层模型。
    使用 RootModel，模型本身就是一个 `Dict[str, GraphDefinition]`。
    """
    
    @field_validator('root')
    @classmethod
    def check_main_graph_exists(cls, v: Dict[str, GraphDefinition]) -> Dict[str, GraphDefinition]:
        """验证器现在作用于 'root' 字段，即模型本身。"""
        if "main" not in v:
            raise ValueError("A 'main' graph must be defined as the entry point.")
        return v
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




# Hevno Engine: JSON 格式与 Map 功能设计规范

本文档定义了 Hevno 引擎的图（Graph）数据格式，并重点阐述了 `map` 和 `call` 这两个核心运行时的设计与实现约定。我们的核心设计哲学是**约定优于配置 (Convention over Configuration)**，旨在通过隐式约定和自动化推断，最大化框架的易用性和表达力。

## 1. 核心数据结构：图集合（Graph Collection）

系统中只有一个顶层概念：**可被命名的图（Graph）的集合**。一个完整的工作流定义就是一个包含一个或多个图的JSON对象。

-   整个配置文件是一个JSON对象，其`key`为图的唯一名称（`Graph ID`），`value`为图的定义。
-   **约定入口图的名称必须为 `"main"`**。引擎执行时将从此图开始。
-   **不再需要 `edges` 字段**。节点间的依赖关系由引擎通过解析宏引用自动推断。

**示例结构:**

```json
{
  "main": {
    "nodes": [
      // ... main graph's nodes ...
    ]
  },
  "process_character_arc": {
    "nodes": [
      // ... nodes for a reusable character processing graph ...
    ]
  }
}
```

## 2. 节点（Node）

节点是图的基本执行单元。

```json
{
  "id": "unique_node_id",
  "data": {
    "runtime": "runtime_name"_or_["runtime_A", "runtime_B"],
    // ... other key-value pairs for runtime configuration ...
  }
}
```

-   `id`: 在其所在的图（Graph）内必须唯一。
-   `data.runtime`: 指定该节点执行一个或一个流水线（pipeline）的运行时。
-   `data` 中的其他字段为运行时的配置参数。

## 3. 宏与依赖推断

引擎通过静态解析节点 `data` 中字符串值的宏 `{{ ... }}` 来自动构建依赖图。

-   **语法:** `{{ <expression> }}`
-   **核心对象:** `nodes`, `vars`, `session` 等。
-   **依赖推断规则:**
    -   当宏的格式为 `{{ nodes.<node_id>.<...> }}` 时，引擎会自动建立从 `<node_id>` 到当前节点的执行依赖。
    -   **重要限制**: 用于依赖推断的 `<node_id>` **目前必须是静态的字面量字符串**。动态的节点引用（如 `{{ nodes[vars.dynamic_id].output }}`）不用于构建初始依赖图，其依赖关系只能在运行时解析，可能导致执行时因依赖未就绪而失败。这将在未来版本中改进。

## 4. 核心运行时

### 4.1 `map` 运行时：Fan-out / Scatter-Gather

`map` 运行时是实现并行迭代的核心。它将一个子图（subgraph）并发地应用到输入列表的每个元素上。

#### **调用格式**

```json
{
  "id": "map_characters",
  "data": {
    "runtime": "system.map",
    // 1. 指定要迭代的列表
    "list": "{{ nodes.data_provider.characters_list }}",
    // 2. 指定要调用的图的名称
    "graph": "process_character_arc",
    // 3. (可选) 精细化地聚合输出
    "collect": "{{ nodes.internal_summary_node.summary }}",
    // 4. 定义如何将外部数据映射到子图的输入占位符
    "using": {
      "character_input": "{{ source.item }}",
      "iteration_info": "{{ source.index }}",
      "external_data": "{{ nodes.some_other_node.value }}"
    }
  }
}
```

#### **核心概念与引擎行为**

1.  **输入占位符 (Input Placeholder):**
    -   在一个被调用的子图（如 `"process_character_arc"`）中，如果一个宏引用了一个**在该图内部不存在的节点ID**（如 `{{ nodes.character_input.name }}`），这个ID (`character_input`) 就被引擎自动识别为一个**输入占位符**。

2.  **输入映射 (`using`):**
    -   `using` 字段的作用是告诉 `map` 运行时如何**满足**子图的输入占位符。
    -   `key` (e.g., `"character_input"`): 必须匹配子图中的输入占位符ID。
    -   `value` (e.g., `"{{ source.item }}"`): 是一个表达式，其值将被注入。
    -   **`source` 对象:** 这是一个特殊的、**只在 `using` 字段的宏表达式中有效**的保留对象，它代表了当前的迭代状态。它包含以下属性：
        -   `source.item`: 当前正在迭代的列表元素。
        -   `source.index`: 当前迭代的从0开始的索引。
        -   `source.list`: 对整个原始迭代列表的引用。

3.  **执行流程:**
    a. `map` 运行时获取 `list` 中的列表。
    b. 对于列表中的每一个 `item`，引擎在内存中创建一个子图的独立执行实例。
    c. 根据 `using` 映射规则，在子图实例的初始状态中**创建虚拟的、已成功的占位符节点**。
    d. 并发地执行所有这些独立的子图实例。
    e. **ID 命名空间:** 为避免冲突，引擎在内部会自动为子图中的节点ID添加唯一前缀。子图内部的宏引用会由引擎自动解析到正确的命名空间。

4.  **输出聚合:**
    -   `map` 运行时会等待所有子图实例执行完毕，并根据 `collect` 字段决定聚合方式：
        -   **如果 `collect` 字段未提供 (默认行为):**
            -   `map` 节点的 `output` 将是一个**列表**，每个元素是对应子图执行的**完整最终状态**。
        -   **如果 `collect` 字段已提供:**
            -   `map` 节点的 `output` 将是一个根据 `collect` 表达式从每个子图提取的值所组成的**扁平列表**。
            -   `collect` 表达式中的 `nodes` 对象指向其所在子图的内部节点。

### 4.2 `call` 运行时：子图调用

`call` 运行时用于实现非迭代式的、单一的子图调用，是代码复用的基础。

#### **调用格式**

```json
{
  "id": "process_main_character",
  "data": {
    "runtime": "system.call",
    "graph": "process_character_arc",
    "using": {
      "character_data": "{{ nodes.main_character_provider.output }}"
    }
  }
}
```

#### **核心概念与引擎行为**

-   **执行流程:**
    -   行为与 `map` 类似，但只执行一次。
    -   根据 `using` 映射，创建虚拟输入节点。
    -   执行 `process_character_arc` 图。
-   **输出:**
    -   `call` 节点的 `output` 就是被调用子图的**完整的最终状态字典**。下游节点可以通过 `{{ nodes.process_main_character.output.internal_summary_node.summary }}` 访问其内部结果。

---
```

### main.py
```
# backend/main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError, BaseModel
from typing import Dict, Any, List, Optional


# 1. 导入新的模型
from backend.models import GraphCollection
from backend.core.engine import ExecutionEngine
from backend.core.registry import runtime_registry
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime, SetWorldVariableRuntime
from backend.core.sandbox_models import Sandbox, SnapshotStore, StateSnapshot
from uuid import UUID
from typing import Dict, Any, List

class CreateSandboxRequest(BaseModel):
    graph_collection: GraphCollection
    initial_state: Optional[Dict[str, Any]] = None


def setup_application():
    app = FastAPI(
        title="Hevno Backend Engine",
        description="The core execution engine for Hevno project, supporting implicit dependency graphs.",
        version="0.2.0-implicit"
    )
    
    runtime_registry.register("system.input", InputRuntime)
    runtime_registry.register("system.template", TemplateRuntime)
    runtime_registry.register("llm.default", LLMRuntime)
    runtime_registry.register("system.set_world_var", SetWorldVariableRuntime)
    # --- 新运行时注册的地方 ---
    # runtime_registry.register("system.map", MapRuntime)
    # runtime_registry.register("system.call", CallRuntime)
    
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
# 全局单例存储 (在生产中应替换为 Redis/DB)
sandbox_store: Dict[UUID, Sandbox] = {}
snapshot_store = SnapshotStore()
execution_engine = ExecutionEngine(registry=runtime_registry)



@app.post("/api/sandboxes", response_model=Sandbox)
async def create_sandbox(
    request: CreateSandboxRequest,
    name: str  # name 作为查询参数
):
    """
    创建一个新的沙盒，并生成其创世快照。
    此版本移除了对 FastAPI 内部 Request 对象的依赖，以实现更纯净的代码。
    """
    try:
        # 业务逻辑核心保持不变
        sandbox = Sandbox(name=name)
        
        # 关键的验证依然在这里发生。
        # 当 GraphCollection 验证失败时（例如缺少 'main'），
        # StateSnapshot 的构造会抛出 Pydantic 的 ValidationError。
        genesis_snapshot = StateSnapshot(
            sandbox_id=sandbox.id,
            graph_collection=request.graph_collection,
            world_state=request.initial_state or {}
        )

    except ValidationError as e:
        # 捕获 Pydantic 验证错误，并将其转换为一个标准的 HTTP 异常。
        # 这避免了与 FastAPI 内部 API 的耦合。
        # 我们返回一个 400 错误，因为请求体的内容在业务上是无效的。
        # 我们将 Pydantic 的错误信息直接放入 detail 中，以方便调试。
        raise HTTPException(
            status_code=400,
            detail=f"Invalid graph definition provided. Details: {e}"
        )

    # 如果代码能执行到这里，说明 StateSnapshot 创建成功
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox
    return sandbox

@app.post("/api/sandboxes/{sandbox_id}/step", response_model=StateSnapshot)
async def execute_sandbox_step(sandbox_id: UUID, user_input: Dict[str, Any]):
    """在沙盒中执行一个步骤，并返回新的状态快照。"""
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
    """获取一个沙盒的所有历史快照。"""
    return snapshot_store.find_by_sandbox(sandbox_id)

@app.put("/api/sandboxes/{sandbox_id}/revert")
async def revert_sandbox_to_snapshot(sandbox_id: UUID, snapshot_id: UUID):
    """将沙盒回滚到指定的历史快照。"""
    sandbox = sandbox_store.get(sandbox_id)
    target_snapshot = snapshot_store.get(snapshot_id)
    if not sandbox or not target_snapshot or target_snapshot.sandbox_id != sandbox.id:
        raise HTTPException(status_code=404, detail="Sandbox or Snapshot not found.")
    sandbox.head_snapshot_id = snapshot_id
    return {"message": f"Sandbox reverted to snapshot {snapshot_id}"}
        
@app.get("/")
def read_root():
    return {"message": "Hevno Backend is running on implicit-dependency architecture!"}

```

### core/templating.py
```
# backend/core/templating.py (最终正确版)
import jinja2
from typing import Any
from backend.core.types import ExecutionContext

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
    
    # 动态构建完整的渲染上下文，适配新版 ExecutionContext
    render_context = {
        "nodes": context.node_states,
        "world": context.world_state,
        "run": context.run_vars,
        "session": context.session_info,
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

### core/types.py
```
# backend/core/types.py (修正版)

from __future__ import annotations
import json 
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field 
from datetime import datetime, timezone

from backend.models import GraphCollection
# StateSnapshot 在这里被 ExecutionContext 引用，但定义在 sandbox_models.py
# sandbox_models.py 又引用了 GraphCollection，形成了循环导入的风险。
# 幸运的是，Python的模块导入机制和 Pydantic 的延迟解析通常能处理好，
# 但为了更清晰，可以把 StateSnapshot 移动到 types.py 或一个更基础的文件中。
# 不过目前问题不大，我们先解决重复字段。
from backend.core.sandbox_models import StateSnapshot 

class ExecutionContext(BaseModel):
    """
    定义一次图执行的完整上下文。
    这是一个纯数据容器，不包含执行逻辑。
    """
    initial_snapshot: StateSnapshot
    node_states: Dict[str, Any] = Field(default_factory=dict)
    world_state: Dict[str, Any] = Field(default_factory=dict)
    run_vars: Dict[str, Any] = Field(default_factory=dict)
    
    # 合并后的定义
    function_registry: Dict[str, Callable] = Field(default_factory=dict)
    session_info: Dict[str, Any] = Field(default_factory=lambda: {
        "start_time": datetime.now(timezone.utc),
        "conversation_turn": 0,  # 保留更完整的定义
    })

    model_config = {
        "arbitrary_types_allowed": True
    }

    @classmethod
    def from_snapshot(cls, snapshot: StateSnapshot, run_vars: Dict[str, Any] = None) -> 'ExecutionContext':
        """工厂方法：从一个快照创建执行上下文。"""
        # 将 run_vars 也作为初始化的一部分
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
        """从当前上下文的状态创建下一个快照。"""
        # 你的文档中提到图可以演化，这意味着 graph_collection 应该从 world_state 中获取
        # 如果它被修改了的话。
        current_graphs = self.initial_snapshot.graph_collection
        # 这是一个示例，你可以定义一个特殊的key来存放演化后的图
        if '__graph_collection__' in self.world_state:
            try:
                # 从 world_state 获取的值可能是 JSON 字符串，需要解析。
                evolved_graph_value = self.world_state['__graph_collection__']
                if isinstance(evolved_graph_value, str):
                    evolved_graph_dict = json.loads(evolved_graph_value)
                else:
                    evolved_graph_dict = evolved_graph_value # It might already be a dict

                evolved_graphs = GraphCollection.model_validate(evolved_graph_dict)
                current_graphs = evolved_graphs
            except Exception as e:
                print(f"Warning: Failed to parse evolved graph collection from world_state: {e}")

        return StateSnapshot(
            sandbox_id=self.initial_snapshot.sandbox_id,
            graph_collection=current_graphs,
            world_state=self.world_state,
            parent_snapshot_id=self.initial_snapshot.id,
            run_output=final_node_states,
            triggering_input=triggering_input
        )
```

### core/sandbox_models.py
```
from __future__ import annotations
from uuid import uuid4, UUID
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

from backend.models import GraphCollection

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

    # --- 使用新的 model_config 语法 ---
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

    def get_latest_snapshot(self, store: 'SnapshotStore') -> Optional[StateSnapshot]:
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
        """清空存储，用于测试隔离。"""
        self._store = {}

```

### core/runtime.py
```
# backend/core/runtime.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class RuntimeInterface(ABC):
    """
    定义所有运行时都必须遵守的接口。
    这是一个纯粹的抽象，不依赖于任何具体的上下文实现。
    """
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行节点逻辑的核心方法。
        
        通过关键字参数 (kwargs) 接收所有上下文信息。
        具体的可用关键字参数由 ExecutionEngine 在调用时提供。
        """
        pass
```

### core/engine.py
```
import asyncio
from enum import Enum, auto
from typing import Dict, Any, Set, List, Optional
from collections import defaultdict

# 导入新的模型和依赖解析器
from backend.models import GraphCollection, GraphDefinition, GenericNode
from backend.core.dependency_parser import build_dependency_graph
from backend.core.registry import RuntimeRegistry
# 从新的中心位置导入类型
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
    """引擎现在执行的是 'step'，从一个快照到下一个快照。"""
    def __init__(self, registry: RuntimeRegistry, num_workers: int = 5):
        self.registry = registry
        self.num_workers = num_workers

    async def step(self, initial_snapshot, triggering_input: Dict[str, Any] = None):
        from backend.core.types import ExecutionContext
        if triggering_input is None:
            triggering_input = {}
        context = ExecutionContext.from_snapshot(initial_snapshot, {"trigger_input": triggering_input})
        main_graph_def = context.initial_snapshot.graph_collection.root.get("main")
        if not main_graph_def:
            raise ValueError("'main' graph not found in the initial snapshot.")
        run = GraphRun(context, main_graph_def)
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
        final_node_states = run.get_final_node_states()
        next_snapshot = context.to_next_snapshot(
            final_node_states=final_node_states,
            triggering_input=triggering_input
        )
        print(f"Step complete. New snapshot {next_snapshot.id} created.")
        return next_snapshot

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
                output = await runtime.execute(
                    step_input=step_input,
                    pipeline_state=pipeline_state,
                    context=context,
                    node=node  # 传递当前节点本身也很有用
                )
                    
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
```

### core/dependency_parser.py
```
# backend/core/dependency_parser.py
import re
from typing import Set, Dict, Any, List

# 正则表达式，用于匹配 {{ nodes.node_id... }} 格式的宏
# - 匹配 '{{' 和 '}}'
# - 捕获 'nodes.' 后面的第一个标识符 (node_id)
# - 这是一个非贪婪匹配，以处理嵌套宏等情况
NODE_DEP_REGEX = re.compile(r'{{\s*nodes\.([a-zA-Z0-9_]+)')

def extract_dependencies_from_string(s: str) -> Set[str]:
    """从单个字符串中提取所有节点依赖。"""
    if not isinstance(s, str):
        return set()
    return set(NODE_DEP_REGEX.findall(s))

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
            # 递归地检查 key 和 value
            deps.update(extract_dependencies_from_value(k))
            deps.update(extract_dependencies_from_value(v))
    return deps

def build_dependency_graph(nodes: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    根据节点列表自动构建依赖图。
    
    返回一个字典，key 是节点ID，value 是其依赖的节点ID集合。
    """
    dependency_map: Dict[str, Set[str]] = {}
    node_ids = {node['id'] for node in nodes}

    for node in nodes:
        node_id = node['id']
        node_data = node.get('data', {})
        
        # 递归地从节点的整个 data 负载中提取依赖
        dependencies = extract_dependencies_from_value(node_data)
        
        # 过滤掉不存在的节点ID，这可能是子图的输入占位符
        valid_dependencies = {dep for dep in dependencies if dep in node_ids}
        
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
# 从新的中心位置导入类型
from backend.core.types import ExecutionContext
from backend.core.templating import render_template
from typing import Dict, Any

class InputRuntime(RuntimeInterface):
    """我只关心 step_input。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        return {"output": step_input.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """我需要 step_input (或 pipeline_state) 来获取模板，需要 context 来渲染。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        pipeline_state = kwargs.get("pipeline_state", {})
        context = kwargs.get("context")

        template_str = step_input.get("template", pipeline_state.get("template", ""))
        if not template_str:
            raise ValueError("TemplateRuntime requires a 'template' string.")
            
        rendered_string = await render_template(template_str, context)
        return {"output": rendered_string}

class LLMRuntime(RuntimeInterface):
    """我需要 step_input/pipeline_state 来获取 prompt，需要 context 来渲染。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        pipeline_state = kwargs.get("pipeline_state", {})
        context = kwargs.get("context")
        
        prompt_template_str = step_input.get("prompt", step_input.get("output", 
                                pipeline_state.get("prompt", "")))
        if not prompt_template_str:
            raise ValueError("LLMRuntime requires a 'prompt' or 'output' string.")

        rendered_prompt = await render_template(prompt_template_str, context)
        
        # 恢复异步行为，模拟 LLM API 调用延迟
        await asyncio.sleep(0.1)  # <--- 恢复这一行
        
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        return {"llm_output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}

# 演示一个只关心 context 的新 Runtime
class SetWorldVariableRuntime(RuntimeInterface):
    """设置一个持久化的世界变量。"""
    async def execute(self, **kwargs) -> Dict[str, Any]:
        step_input = kwargs.get("step_input", {})
        context = kwargs.get("context")
        variable_name = step_input.get("variable_name")
        value_to_set = step_input.get("value")
        if not variable_name:
            raise ValueError("SetWorldVariableRuntime requires 'variable_name'.")
        # 修改的是可变的 world_state
        context.world_state[variable_name] = value_to_set
        return {}
```
