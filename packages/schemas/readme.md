# @hevno/schemas

> Hevno 平台的核心数据结构与类型定义

`@hevno/schemas` 是 Hevno 生态系统的基石。它使用 [Zod](https://zod.dev/) 定义了所有核心概念（如计算图、节点、边、端口）的不可变契约。这个包的目标是为前端 UI、后端执行引擎和第三方插件提供一个统一、可靠、类型安全的数据标准。

## 设计理念：极简主义与极致可配置

我们的核心设计哲学是 **“拒绝类型爆炸，拥抱配置组合”**。

在许多工作流或节点编辑器系统中，功能的增加往往伴随着新节点类型的涌入（如 `If-Else Node`, `Loop Node`, `Sub-Flow Node` 等）。这种方式虽然直观，但长期来看会导致系统变得复杂、僵化，并增加用户的学习成本。

Hevno 采取了截然不同的方法：

1.  **极简的节点集合**: 我们将节点类型严格限制在最基础、最正交的三种：
    *   `InputNode`: 图的数据入口。
    *   `OutputNode`: 图的数据出口。
    *   `ProcessorNode`: **唯一的“工作马”**。所有实际的计算、逻辑、调用和控制流都由它承载。

2.  **行为由运行时配置决定**: `ProcessorNode` 的强大之处在于其 `runtime` 属性。它不是一个静态的节点，而是一个“变色龙”，其具体行为（是调用 LLM，还是执行一段代码，或是其他任何事）完全由其运行时配置决定。这使得我们可以通过增加新的 `runtime` 类型来无限扩展功能，而无需修改基础节点结构。

3.  **元能力下沉为核心函数**: 像“调用子图”或“读写全局变量”这样的系统级“元能力”，我们不将其实现为特殊的节点类型。相反，它们被实现为内置的、由 `ProcessorNode` 调用的**核心函数**（如 `core:runGraph`, `core:setVariable`）。这使得系统的核心功能和用户自定义功能在结构上完全等价，极大地增强了统一性和灵活性。

这种设计使得 Hevno 的图不仅是数据的流向图，更是一个通过配置来定义的、可编程的计算结构。

## 核心 API (Schemas)

所有 Schema 均由 `zod` 构建，提供了编译时类型安全和运行时验证。

### `ValueTypeSchema` 

这是 Hevno 类型系统的核心。`ValueType` 不是一个固定的类型，而是一个描述数据结构的元定义。它允许我们动态地定义任意复杂的数据类型，例如字符串、数字、布尔值、对象和数组。

-   `type: 'string' | 'number' | 'boolean' | 'any'`: 基础类型。
-   `type: 'object', properties: Record<string, ValueType>`: 描述一个对象及其属性的类型。
-   `type: 'array', item: ValueType`: 描述一个数组及其元素的类型。

这个元 schema 是实现动态端口类型和函数签名的关键。

### `GraphSchema`

图的顶层结构。

-   `id: string`: 图的唯一标识。
-   `name: string`: 图的名称。
-   `nodes: GraphNode[]`: 构成图的所有节点数组。
-   `edges: Edge[]`: 连接节点的边数组。
-   `variables?: Record<string, any>`: 图级别的全局变量，用于跨节点共享状态。
-   `subgraphs?: Record<string, GraphSchema>`: 嵌套的子图定义，用于封装和复用逻辑。

### `GraphNodeSchema`

一个可辨识联合类型 (discriminated union)，包含以下几种节点：

#### `InputNodeSchema`
-   `type: 'input'`
-   `outputs: Port[]`: 定义该入口节点能提供哪些数据端口。

#### `OutputNodeSchema`
-   `type: 'output'`
-   `inputs: Port[]`: 定义该出口节点需要接收哪些数据端口。

#### `ProcessorNodeSchema`
-   `type: 'processor'`
-   `inputs: Port[]`: 输入端口。
-   `outputs: Port[]`: 输出端口。
-   `runtime`: 定义其行为，可以是：
    -   `LlmRuntimeSchema`: 配置一个 LLM 调用，包含 `provider`, `model`, `userPrompt` (支持模板)等。
    -   `FunctionRuntimeSchema`: 配置一个函数调用，包含 `functionName`，以及可选的 `inputSchema` 和 `outputSchema`，它们使用 `ValueTypeSchema` 来定义函数的输入输出数据结构。

### `PortSchema`

定义节点的连接点。

-   `id: string`: 端口的唯一 ID。
-   `name: string`: 端口的可读名称。
-   `valueType: ValueType`: **核心字段**。使用 `ValueTypeSchema` 定义该端口传输的数据类型。默认为 `{ type: 'any' }`。这使得编辑器和引擎可以在运行时理解和验证数据。
-   `kind: 'data' | 'control'`: **关键字段**。`'data'` 表示传递数据，`'control'` 表示仅用于定义执行顺序，不传递数据。这使得控制流和数据流可以在图中被明确区分。

### `EdgeSchema`

定义节点间的连接。

-   `sourceNodeId`, `sourceOutputId`: 连接的起点（节点ID和端口ID）。
-   `targetNodeId`, `targetInputId`: 连接的终点（节点ID和端口ID）。

## 运行时验证器 (新增)

为了让 `ValueType` 定义真正发挥作用，`@hevno/schemas` 包还提供了一组辅助函数，用于将这些元类型定义编译成可执行的 Zod 验证器。

### `buildZodValidatorFromValueType(valueType: ValueType): ZodTypeAny`

递归地将一个 `ValueType` 对象构建成一个 Zod 验证器。

```typescript
import { buildZodValidatorFromValueType } from '@hevno/schemas';

const myType = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    age: { type: 'number' },
  }
};

const validator = buildZodValidatorFromValueType(myType);

validator.parse({ name: "Alice", age: 30 }); // OK
validator.parse({ name: "Bob", age: "unknown" }); // Throws ZodError
```

### `buildObjectValidatorFromSchema(schema: Record<string, ValueType>): ZodObject`

这是一个便捷函数，专门用于为 `FunctionRuntime` 的 `inputSchema` 或 `outputSchema` 构建整个对象的验证器。

```typescript
import { buildObjectValidatorFromSchema, FunctionRuntime } from '@hevno/schemas';

const func: FunctionRuntime = {
  type: 'function',
  functionName: 'myFunc',
  inputSchema: {
    user: { type: 'string' },
    count: { type: 'number' },
  }
};

if (func.inputSchema) {
  const inputValidator = buildObjectValidatorFromSchema(func.inputSchema);
  // inputValidator is now a z.object({ user: z.string(), count: z.number() })
}
```

## 使用

```typescript
import { GraphSchema, Graph } from '@hevno/schemas';

const myGraph: Graph = {
  // ... a graph object
};

// Zod will validate the structure at runtime
try {
  GraphSchema.parse(myGraph);
  console.log("Graph is valid!");
} catch (e) {
  console.error("Invalid graph structure:", e);
}
```