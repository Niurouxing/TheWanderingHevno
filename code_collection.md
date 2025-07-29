### requirements.txt
```
annotated-types==0.7.0
anyio==4.9.0
certifi==2025.7.14
click==8.2.1
dnspython==2.7.0
email_validator==2.2.0
fastapi==0.116.1
fastapi-cli==0.0.8
fastapi-cloud-cli==0.1.5
h11==0.16.0
httpcore==1.0.9
httptools==0.6.4
httpx==0.28.1
idna==3.10
iniconfig==2.1.0
itsdangerous==2.2.0
Jinja2==3.1.6
markdown-it-py==3.0.0
MarkupSafe==3.0.2
mdurl==0.1.2
orjson==3.11.1
packaging==25.0
pluggy==1.6.0
pydantic==2.11.7
pydantic-extra-types==2.10.5
pydantic-settings==2.10.1
pydantic_core==2.33.2
Pygments==2.19.2
pytest==8.4.1
pytest-asyncio==1.1.0
pytest-mock==3.14.1
python-dotenv==1.1.1
python-multipart==0.0.20
PyYAML==6.0.2
rich==14.1.0
rich-toolkit==0.14.9
rignore==0.6.4
sentry-sdk==2.33.2
shellingham==1.5.4
sniffio==1.3.1
starlette==0.47.2
typer==0.16.0
typing-inspection==0.4.1
typing_extensions==4.14.1
ujson==5.10.0
urllib3==2.5.0
uvicorn==0.35.0
uvloop==0.21.0
watchfiles==1.1.0
websockets==15.0.1

```

### frontend/tsconfig.node.json
```
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}

```

### frontend/index.html
```
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React + TS</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

```

### frontend/tsconfig.app.json
```
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}

```

### frontend/README.md
```
# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

```

### frontend/package.json
```
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.11.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "reactflow": "^11.11.4"
  },
  "devDependencies": {
    "@eslint/js": "^9.30.1",
    "@types/react": "^19.1.8",
    "@types/react-dom": "^19.1.6",
    "@vitejs/plugin-react": "^4.6.0",
    "eslint": "^9.30.1",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.20",
    "globals": "^16.3.0",
    "typescript": "~5.8.3",
    "typescript-eslint": "^8.35.1",
    "vite": "^7.0.4"
  }
}

```

### frontend/tsconfig.json
```
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}

```

### frontend/eslint.config.js
```
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { globalIgnores } from 'eslint/config'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])

```

### tests/test_03_executor.py
```
# tests/test_03_executor.py
import pytest
from unittest.mock import patch
from backend.core.executor import GraphExecutor
from backend.models import Graph, GenericNode, Edge

# 使用 pytest.mark.usefixtures 来自动应用 fixture
@pytest.mark.usefixtures("fresh_runtime_registry")
@pytest.mark.asyncio
async def test_graph_executor_linear_flow(simple_linear_graph, mocker):
    # 我们仍然需要mock掉LLM的外部调用
    mocker.patch(
        "backend.runtimes.base_runtimes.asyncio.sleep", 
        return_value=None
    )

    executor = GraphExecutor()
    final_state = await executor.execute(simple_linear_graph)

    # 断言最终状态
    assert "node_A" in final_state
    assert final_state["node_A"]["output"] == "A story about a cat."

    assert "node_B" in final_state
    expected_llm_input = "Continue this story: A story about a cat."
    assert final_state["node_B"]["output"] == f"LLM_RESPONSE_FOR:[{expected_llm_input}]"

    assert "node_C" in final_state
    expected_final_output = f"The final story is: {final_state['node_B']['output']}"
    assert final_state["node_C"]["output"] == expected_final_output

@pytest.mark.usefixtures("fresh_runtime_registry")
@pytest.mark.asyncio
async def test_graph_executor_handles_runtime_error(mocker):
    # 模拟一个会出错的LLM Runtime
    mocker.patch(
        "backend.runtimes.base_runtimes.LLMRuntime.execute",
        side_effect=IOError("LLM API is down")
    )

    graph = Graph(
        nodes=[
            GenericNode(id="A", type="input", data={"runtime": "system.input", "value": "test"}),
            GenericNode(id="B", type="default", data={"runtime": "llm.default", "prompt": "{{ A.output }}"}),
        ],
        edges=[]
    )
    
    executor = GraphExecutor()
    final_state = await executor.execute(graph)
    
    assert "A" in final_state
    assert final_state["A"]["output"] == "test"
    
    # 检查错误是否被正确捕获并记录在状态中
    assert "B" in final_state
    assert "error" in final_state["B"]
    assert "LLM API is down" in final_state["B"]["error"]
```

### tests/test_02_runtimes.py
```
# tests/test_02_runtimes.py
import pytest
from backend.core.runtime import ExecutionContext
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime

# ---- 测试 InputRuntime ----
@pytest.mark.asyncio
async def test_input_runtime():
    runtime = InputRuntime()
    node_data = {"value": "Hello World"}
    context = ExecutionContext(state={}, graph=None, function_registry={})
    
    result = await runtime.execute(node_data, context)
    
    assert result == {"output": "Hello World"}

# ---- 测试 TemplateRuntime ----
@pytest.mark.asyncio
async def test_template_runtime_simple():
    runtime = TemplateRuntime()
    node_data = {"template": "The value is: {{ node_A.output }}"}
    context = ExecutionContext(
        state={"node_A": {"output": "SUCCESS"}},
        graph=None,
        function_registry={}
    )
    
    result = await runtime.execute(node_data, context)
    
    assert result == {"output": "The value is: SUCCESS"}

@pytest.mark.asyncio
async def test_template_runtime_missing_variable_raises_error():
    runtime = TemplateRuntime()
    node_data = {"template": "Value: {{ non_existent.output }}"}
    context = ExecutionContext(state={}, graph=None, function_registry={})
    
    # Jinja2会抛出 UndefinedError，我们捕获它并包装为IOError
    with pytest.raises(IOError, match="Template rendering failed"):
        await runtime.execute(node_data, context)

# ---- 测试 LLMRuntime (关键：使用 Mock) ----
@pytest.mark.asyncio
async def test_llm_runtime_with_mock(mocker): # 使用 pytest-mock 的 mocker fixture
    # 1. Mock掉真正的LLM调用（这里我们假设它是一个异步函数）
    # 注意：我们mock的是它在运行时模块中被调用的地方
    mocked_llm_call = mocker.patch(
        "backend.runtimes.base_runtimes.asyncio.sleep", # 在MVP中我们用sleep模拟
        return_value=None # asyncio.sleep不返回任何东西
    )
    
    runtime = LLMRuntime()
    node_data = {"prompt": "Summarize: {{ input.text }}"}
    context = ExecutionContext(
        state={"input": {"text": "A very long story."}},
        graph=None,
        function_registry={}
    )
    
    result = await runtime.execute(node_data, context)

    # 2. 断言结果是否基于模拟的 LLM 响应
    expected_prompt = "Summarize: A very long story."
    assert "output" in result
    assert result["output"] == f"LLM_RESPONSE_FOR:[{expected_prompt}]"
    assert "summary" in result

    # 3. 断言 mock 的函数是否被调用了
    mocked_llm_call.assert_awaited_once_with(1)
```

### tests/conftest.py
```
# tests/conftest.py
import pytest
from backend.core.registry import RuntimeRegistry
from backend.runtimes.base_runtimes import InputRuntime, TemplateRuntime, LLMRuntime
from backend.models import Graph, GenericNode, Edge

@pytest.fixture(scope="function") # 'function' scope表示每个测试函数都会获得一个新的实例
def fresh_runtime_registry():
    """提供一个干净的、预填充了基础运行时的注册表实例。"""
    registry = RuntimeRegistry()
    registry.register("system.input", InputRuntime)
    registry.register("system.template", TemplateRuntime)
    registry.register("llm.default", LLMRuntime)
    return registry

@pytest.fixture
def simple_linear_graph():
    """提供一个简单的线性图，用于测试执行流程。"""
    return Graph(
        nodes=[
            GenericNode(id="node_A", type="input", data={"runtime": "system.input", "value": "A story about a cat."}),
            GenericNode(id="node_B", type="default", data={"runtime": "llm.default", "prompt": "Continue this story: {{ node_A.output }}"}),
            GenericNode(id="node_C", type="output", data={"runtime": "system.template", "template": "The final story is: {{ node_B.output }}"}),
        ],
        edges=[
            Edge(source="node_A", target="node_B"),
            Edge(source="node_B", target="node_C"),
        ]
    )
```

### tests/__init__.py
```

```

### tests/test_01_models.py
```
# tests/test_01_models.py
import pytest
from pydantic import ValidationError
from backend.models import GenericNode, Graph

def test_generic_node_validation():
    # 有效数据
    valid_data = {"id": "1", "type": "default", "data": {"runtime": "test"}}
    node = GenericNode(**valid_data)
    assert node.id == "1"
    assert node.data["runtime"] == "test"

    # 缺少 runtime 会导致 data 字段验证失败（虽然我们没有明确要求，但通常是需要的）
    # Pydantic 默认所有字段都是必须的，除非有默认值或 Optional
    # 但我们这里是data字段本身必须存在，其内容可以灵活
    valid_data_no_runtime = {"id": "2", "type": "default", "data": {}}
    node_no_runtime = GenericNode(**valid_data_no_runtime)
    assert node_no_runtime.data == {}


    # 缺少 id 字段应该会失败
    with pytest.raises(ValidationError):
        GenericNode(type="default", data={"runtime": "test"})

def test_graph_model(simple_linear_graph): # 使用我们定义的fixture
    """测试Graph模型能否正确加载一个合法的图结构。"""
    graph = simple_linear_graph
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.nodes[0].id == "node_A"
```

### backend/models.py
```
# backend/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Edge模型保持不变
class Edge(BaseModel):
    source: str
    target: str

# 这是关键的重构：我们不再使用字面量类型 (Literal)
# 而是创建一个通用的节点模型
class GenericNode(BaseModel):
    id: str
    # 'type' 字段现在只用于前端UI渲染的提示，例如'input', 'output', 'default'
    # 它不再决定后端的执行逻辑
    type: str 
    
    # data 字段中包含了一个新的关键属性 'runtime'
    data: Dict[str, Any] = Field(
        ...,
        description="节点的核心配置，必须包含 'runtime' 字段来指定执行器"
    )

class Graph(BaseModel):
    nodes: List[GenericNode]
    edges: List[Edge]
```

### backend/main.py
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
graph_executor = GraphExecutor()

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

### backend/core/registry.py
```
# backend/core/registry.py
from typing import Dict, Type
from backend.core.runtime import RuntimeInterface

class RuntimeRegistry:
    def __init__(self):
        self._runtimes: Dict[str, RuntimeInterface] = {}

    def register(self, name: str, runtime_class: Type[RuntimeInterface]):
        if name in self._runtimes:
            print(f"Warning: Overwriting runtime '{name}'.")
        # 我们在这里实例化运行时
        self._runtimes[name] = runtime_class()
        print(f"Runtime '{name}' registered.")

    def get_runtime(self, name: str) -> RuntimeInterface:
        runtime = self._runtimes.get(name)
        if runtime is None:
            raise ValueError(f"Runtime '{name}' not found.")
        return runtime

# 创建一个全局单例
runtime_registry = RuntimeRegistry()
```

### backend/core/__init__.py
```

```

### backend/core/runtime.py
```
# backend/runtimes/base_runtimes.py

from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点的运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 输入节点直接将其 'value' 作为输出
        return {"output": node_data.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """一个通用的模板渲染运行时，可用于输出或任何需要格式化文本的地方"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        template_str = node_data.get("template", "")
        try:
            template = template_env.from_string(template_str)
            # 注意这里，我们把整个 state 传给 Jinja2
            rendered_string = await template.render_async(context.state)
            return {"output": rendered_string}
        except Exception as e:
            # 在未来，这里应该有一个更健壮的错误处理机制
            raise IOError(f"Template rendering failed: {e}")

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        prompt_template_str = node_data.get("prompt", "")
        
        # 渲染模板，从上下文中注入依赖数据
        try:
            template = template_env.from_string(prompt_template_str)
            rendered_prompt = await template.render_async(context.state)
        except Exception as e:
            raise IOError(f"Prompt template rendering failed: {e}")

        # --- 模拟LLM调用 ---
        print(f"  - Calling LLM with Prompt: {rendered_prompt}")
        await asyncio.sleep(1) # 模拟网络延迟
        
        # 真实的LLM调用逻辑会在这里
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        # LLM运行时可以有多个输出，例如，一个用于对话，一个用于总结
        return {"output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}
```

### backend/core/executor.py
```
# backend/core/executor.py
from backend.models import Graph
from backend.core.registry import runtime_registry
from backend.core.runtime import ExecutionContext
from typing import Dict, Any

class GraphExecutor:
    async def execute(self, graph: Graph) -> Dict[str, Any]:
        # 这是一个更健壮的拓扑排序实现
        # （这里为了简洁，我们仍然用一个简化版，但结构已经准备好了）
        node_map = {node.id: node for node in graph.nodes}
        
        # 待办: 实现一个真正的拓扑排序算法来确定 execution_order
        execution_order = sorted(graph.nodes, key=lambda n: n.id)

        # 初始上下文
        exec_context = ExecutionContext(
            state={},
            graph=graph,
            function_registry={} # 暂时为空，未来用于元能力
        )

        for node in execution_order:
            node_id = node.id
            runtime_name = node.data.get("runtime")
            
            if not runtime_name:
                print(f"Warning: Node {node_id} has no runtime. Skipping.")
                continue

            print(f"Executing node: {node_id} with runtime: {runtime_name}")

            try:
                # 从注册表获取运行时实例
                runtime = runtime_registry.get_runtime(runtime_name)
                
                # 执行并更新状态
                output = await runtime.execute(node.data, exec_context)
                exec_context.state[node_id] = output

            except Exception as e:
                # 统一的错误处理
                error_message = f"Error executing node {node_id} ({runtime_name}): {e}"
                print(error_message)
                # 将错误信息存入状态，以便前端显示
                exec_context.state[node_id] = {"error": error_message}
                # 可以在这里决定是中断执行还是继续
                break 

        print("Graph execution finished.")
        return exec_context.state
```

### backend/runtimes/__init__.py
```
# backend/runtimes/base_runtimes.py
from backend.core.runtime import RuntimeInterface, ExecutionContext
from typing import Dict, Any
import jinja2
import asyncio

template_env = jinja2.Environment(enable_async=True)

class InputRuntime(RuntimeInterface):
    """处理输入节点的运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # 输入节点直接将其 'value' 作为输出
        return {"output": node_data.get("value", "")}

class TemplateRuntime(RuntimeInterface):
    """一个通用的模板渲染运行时，可用于输出或任何需要格式化文本的地方"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        template_str = node_data.get("template", "")
        try:
            template = template_env.from_string(template_str)
            # 注意这里，我们把整个 state 传给 Jinja2
            rendered_string = await template.render_async(context.state)
            return {"output": rendered_string}
        except Exception as e:
            # 在未来，这里应该有一个更健壮的错误处理机制
            raise IOError(f"Template rendering failed: {e}")

class LLMRuntime(RuntimeInterface):
    """处理LLM调用的运行时"""
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        prompt_template_str = node_data.get("prompt", "")
        
        # 渲染模板，从上下文中注入依赖数据
        try:
            template = template_env.from_string(prompt_template_str)
            rendered_prompt = await template.render_async(context.state)
        except Exception as e:
            raise IOError(f"Prompt template rendering failed: {e}")

        # --- 模拟LLM调用 ---
        print(f"  - Calling LLM with Prompt: {rendered_prompt}")
        await asyncio.sleep(1) # 模拟网络延迟
        
        # 真实的LLM调用逻辑会在这里
        llm_response = f"LLM_RESPONSE_FOR:[{rendered_prompt}]"
        
        # LLM运行时可以有多个输出，例如，一个用于对话，一个用于总结
        return {"output": llm_response, "summary": f"Summary of '{rendered_prompt[:20]}...'"}
```

### backend/runtimes/base_runtimes.py
```

```

### frontend/src/App.tsx
```
import { useState, useCallback } from 'react';
import ReactFlow, {
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  // 使用 'type' 关键字显式导入类型
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';

// MVP阶段的初始节点和边
const initialNodes: Node[] = [
  {
    id: 'node_A',
    type: 'input', // React Flow的默认输入节点
    position: { x: 100, y: 50 },
    data: { label: 'Input Node' },
  },
  {
    id: 'node_B',
    type: 'default', // 代表我们的LLMNode
    position: { x: 100, y: 200 },
    data: { label: 'LLM Node' },
  },
  {
    id: 'node_C',
    type: 'output', // React Flow的默认输出节点
    position: { x: 100, y: 350 },
    data: { label: 'Output Node' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: 'node_A', target: 'node_B' },
];

// 我们后端API的地址
const API_URL = 'http://localhost:8000/api/graphs/execute';

function App() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [result, setResult] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    []
  );

  const handleRunGraph = async () => {
    setIsLoading(true);
    setResult('Executing graph...');

    // 将React Flow的格式转换为我们后端定义的格式
    const graphPayload = {
      nodes: [
        { id: 'node_A', type: 'InputNode', data: { value: 'Tell me a short story about a robot.' } },
        { id: 'node_B', type: 'LLMNode', data: { prompt: '{{node_A.output}}' } },
        { id: 'node_C', type: 'OutputNode', data: { template: 'Final result is: {{node_B.output}}' } },
      ],
      edges: edges.map(e => ({ source: e.source, target: e.target })),
    };

    try {
      const response = await axios.post(API_URL, graphPayload);
      // 我们只显示最后一个节点的输出作为最终结果
      setResult(JSON.stringify(response.data['node_C'], null, 2));
    } catch (error: any) {
      setResult(`Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '10px', background: '#333', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Hevno MVP</h1>
        <button onClick={handleRunGraph} disabled={isLoading}>
          {isLoading ? 'Running...' : 'Run Graph'}
        </button>
      </header>
      <div style={{ flex: 1, display: 'flex' }}>
        <div style={{ flex: '2' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
          >
            <Controls />
            <Background />
          </ReactFlow>
        </div>
        <div style={{ flex: '1', padding: '10px', background: '#2a2a2a', overflowY: 'auto' }}>
          <h2>Result</h2>
          <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word', color: 'lightgreen' }}>
            {result}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default App;
```

### frontend/src/main.tsx
```
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

```

### frontend/src/index.css
```
:root {
    font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
    line-height: 1.5;
    font-weight: 400;
    color-scheme: light dark;
    color: rgba(255, 255, 255, 0.87);
    background-color: #242424;
}

body {
    margin: 0;
    display: flex;
    place-items: center;
    min-width: 320px;
    min-height: 100vh;
}

#root {
    width: 100%;
    height: 100vh;
}
```

### frontend/src/vite-env.d.ts
```
/// <reference types="vite/client" />

```
