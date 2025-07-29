
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

## 项目结构

```
.
├── backend/
│   ├── core/                  # 引擎的核心组件
│   │   ├── executor.py        # 图执行器
│   │   ├── registry.py        # 运行时注册表
│   │   └── runtime.py         # 运行时接口和执行上下文定义
│   ├── models.py              # Pydantic 数据模型 (Graph, Node, Edge)
│   ├── runtimes/              # 内置的运行时实现
│   │   └── base_runtimes.py   # 如 LLM, Input, Template 等基础运行时
│   └── main.py                # FastAPI 应用入口，负责API暴露和组装
├── tests/                     # 自动化测试目录
│   ├── conftest.py            # Pytest 全局测试配置和 fixtures
│   └── test_*.py              # 各模块的单元测试
└── ...
```

## 工作原理

一次典型的图执行流程如下：

1.  **API 请求**: 前端或客户端将一个 `Graph` 结构的JSON对象 POST到 `/api/graphs/execute` 端点。

2.  **执行器初始化**: `GraphExecutor` 接收到图对象。它依赖于一个**运行时注册表 (RuntimeRegistry)**，该注册表在应用启动时被填充。

3.  **拓扑排序**: 执行器分析图的节点和边，确定一个无环的执行顺序（*当前版本为简化实现，未来将支持完整拓扑排序*）。

4.  **顺序执行**:
    *   执行器遍历每一个节点。
    *   它读取节点的 `data.runtime` 字段 (例如, `"llm.default"`)。
    *   它向 `RuntimeRegistry` 请求与该名称匹配的运行时实例。
    *   它调用该运行时实例的 `.execute()` 方法，并将**执行上下文 (ExecutionContext)** 传递给它。

5.  **上下文驱动**: `ExecutionContext` 是一个关键对象，它包含了：
    *   `state`: 一个字典，存储了所有已执行节点的输出。
    *   `graph`: 对当前整个图对象的引用。
    *   `function_registry`: 一个未来用于实现“元能力”的函数集合。

    这使得任何一个运行时，在执行时都能访问到全局状态，实现复杂的依赖注入和数据流（例如，通过Jinja2模板 `{{ node_A.output }}`）。

6.  **状态更新**: 每个运行时执行完毕后，其返回的字典会被存入 `state` 中，以该节点的ID为键。

7.  **返回结果**: 整个图执行完毕后，最终的 `state` 字典作为API响应返回。

## 如何运行

### 1. 环境设置

- 确保您已安装 Python 3.10+。
- 建议使用虚拟环境：
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # on Windows: .venv\Scripts\activate
  ```
- 安装依赖：
  ```bash
  pip install -r requirements.txt
  ```

### 2. 启动开发服务器

```bash
uvicorn backend.main:app --reload
```
服务将在 `http://localhost:8000` 上运行。`--reload` 参数使得代码修改后服务会自动重启。

### 3. API 交互

您可以使用任何API客户端（如 Postman, Insomnia, หรือ `curl`）或访问自动生成的API文档 `http://localhost:8000/docs` 来与后端交互。

**示例 `curl` 请求:**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/graphs/execute' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "nodes": [
    {
      "id": "node_A",
      "type": "input",
      "data": {
        "runtime": "system.input",
        "value": "Tell me a short story about a brave knight."
      }
    },
    {
      "id": "node_B",
      "type": "default",
      "data": {
        "runtime": "llm.default",
        "prompt": "{{ node_A.output }}"
      }
    },
    {
      "id": "node_C",
      "type": "output",
      "data": {
        "runtime": "system.template",
        "template": "The final story is: {{ node_B.output }}"
      }
    }
  ],
  "edges": [
    {
      "source": "node_A",
      "target": "node_B"
    },
    {
      "source": "node_B",
      "target": "node_C"
    }
  ]
}'
```

## 运行测试

我们使用 `pytest` 进行自动化测试。测试是保证代码质量和实现安全重构的基石。

1.  安装开发依赖 (如果尚未安装):
    ```bash
    pip install pytest pytest-asyncio pytest-mock
    ```

2.  运行所有测试:
    ```bash
    pytest
    ```

## 如何扩展 (插件开发)

得益于我们的核心设计，添加新功能变得异常简单，且无需修改任何核心代码。

要创建一个新的功能，比如一个“执行Python代码”的节点，您只需要：

1.  **创建运行时类**: 定义一个新类，继承自 `backend.core.runtime.RuntimeInterface`，并实现 `execute` 方法。
    ```python
    # plugins/my_plugin/code_runtime.py
    from backend.core.runtime import RuntimeInterface, ExecutionContext

    class PythonCodeRuntime(RuntimeInterface):
        async def execute(self, node_data, context):
            code = node_data.get("code", "")
            # 注意：真实的实现需要一个安全的沙箱环境！
            # exec(code, {"context": context})
            return {"result": "Code executed."}
    ```

2.  **注册运行时**: 在您的插件加载逻辑中（未来将有专门的插件加载器），将您的新运行时注册到全局注册表中。
    ```python
    # plugins/my_plugin/loader.py
    from backend.core.registry import runtime_registry
    from .code_runtime import PythonCodeRuntime

    def register_plugin():
        runtime_registry.register("code.python", PythonCodeRuntime)
    ```

完成！现在，用户可以在前端创建一个节点，并将其 `runtime` 设置为 `"code.python"`，引擎就会自动调用您的新逻辑。