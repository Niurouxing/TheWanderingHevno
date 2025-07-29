# @hevno/core-engine

> Hevno 平台的高性能、可扩展的图执行引擎

`@hevno/core-engine` 是 Hevno 的大脑。它负责接收一个遵循 `@hevno/schemas` 规范的计算图（Graph），并根据其结构和配置，异步地、高效地执行其中的每一个节点，最终产出结果。

## 设计理念：依赖注入与分层职责

引擎的设计严格遵循关注点分离 (Separation of Concerns) 和依赖注入 (Dependency Injection) 的原则，旨在实现最大的可测试性、可扩展性和可维护性。

1.  **统一的执行入口 (`GraphExecutor`)**: `GraphExecutor` 是与外部世界交互的唯一入口。它负责整个图的生命周期管理，包括：
    *   **拓扑排序**: 使用 Kahn 算法确定无环图的正确执行顺序。
    *   **上下文管理**: 创建并维护一个 `ExecutionContext`，包含所有节点的输出和全局变量状态。
    *   **调度与委托**: 遍历排序后的节点，并将具体的执行任务委托给相应的 `Runner`。

2.  **可插拔的执行器 (`Runners`)**: 针对 `ProcessorNode` 的每一种 `runtime` 类型，都有一个专门的 `Runner` 负责其执行逻辑。
    *   `LlmRunner`: 负责处理所有 `runtime.type === 'llm'` 的节点。它管理与 LLM API 的通信、处理 Prompt 模板、解析返回结果。
    *   `FunctionRunner`: 负责处理所有 `runtime.type === 'function'` 的节点。它维护一个函数注册表，并执行匹配的函数。
    这种设计意味着，如果我们想支持一种新的运行时（比如 `HttpRunner` 或 `CodeRunner`），我们只需要创建一个新的 Runner 类并注册到 `GraphExecutor` 中，而无需改动引擎的核心逻辑。

3.  **通过服务注入核心能力 (`CoreServices`)**: 引擎中的某些部分需要调用其他核心功能（例如，`FunctionRunner` 中的 `core:runGraph` 函数需要能够执行另一个图，这就需要调用 `GraphExecutor`）。为了避免混乱的循环依赖，我们引入了一个 `CoreServices` 对象。这个对象由 `GraphExecutor` 创建，并通过依赖注入的方式传递给所有 `Runner` 和核心函数。它包含了像 `graphExecutor` 实例和 `graphRegistry` 等系统级服务，为核心功能提供了干净、受控的“后门”。

4.  **强大的模板系统 (`TemplateResolver`)**: 灵活性的一大来源是模板字符串 `{{...}}`。我们提供了一个独立的 `resolveTemplate` 工具，它能够智能地解析 `{{nodeId.outputId}}` 或 `{{variables.varName}}` 这样的占位符。它不仅能处理字符串替换，还能在占位符是模板的唯一内容时，返回原始数据类型（如对象、数组），这对于将复杂数据结构从一个节点传递到另一个节点至关重要。

## 核心 API

### `GraphExecutor`

引擎的主类。

-   **`constructor()`**: 初始化所有 Runners 和核心服务。
-   **`async execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext>`**:
    -   `graph`: 一个符合 `GraphSchema` 的图对象。
    -   `initialInputs`: 一个对象，其键是 `InputNode` 的 ID，值是该节点的初始输出数据。
    -   返回一个 `Promise`，其结果是包含所有节点输出和最终变量状态的 `ExecutionContext`。

### Runners (`INodeRunner` 接口)

所有执行器的共同接口。

-   **`async run(node, inputs, context, services): Promise<Record<string, any>>`**:
    -   `node`: 当前要执行的 `ProcessorNode`。
    -   `inputs`: 从上游节点连接到当前节点的数据输入。
    -   `context`: 整个图的当前执行上下文。
    -   `services`: 核心服务注入对象。
    -   返回一个对象，其键是该节点的输出端口 ID，值是对应的输出数据。

### 核心函数

`FunctionRunner` 内置了一系列以 `core:` 为前缀的强大函数，它们构成了系统的元能力。

-   **`core:setVariable`**: 设置一个全局变量。
    -   输入: `{ name: string, value: any }`
-   **`core:getVariable`**: 获取一个全局变量。
    -   输入: `{ name: string }`
    -   输出: `{ value: any }`
-   **`core:runGraph`**: 递归执行一个在 `graph.subgraphs` 中定义的子图。
    -   输入: `{ graphId: string, ...restInputs }` (其余输入会作为子图的初始输入)
    -   输出: 子图的 `OutputNode` 的结果。

## 使用示例

```typescript
import { GraphExecutor } from '@hevno/core-engine';
import { Graph } from '@hevno/schemas';

// 1. 定义一个图
const myGraph: Graph = { /* ... a complex graph ... */ };

// 2. 准备初始输入
const inputs = {
  'my-input-node-id': {
    'topic': 'AI playing RPGs'
  }
};

// 3. 实例化并执行
const executor = new GraphExecutor();
try {
  const resultContext = await executor.execute(myGraph, inputs);
  
  // 4. 获取最终输出
  const finalOutput = resultContext.outputs['my-output-node-id'];
  console.log('Final output:', finalOutput);
} catch (error) {
  console.error('Graph execution failed:', error);
}