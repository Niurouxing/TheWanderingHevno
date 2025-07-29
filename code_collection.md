### readme.md
```
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
```

### package.json
```
{
    "name": "@hevno/schemas",
    "version": "1.0.0",
    "type": "module",
    "main": "./dist/index.js",
    "types": "./dist/index.d.ts",
    "exports": {
        ".": {
            "import": "./dist/index.js",
            "require": "./dist/index.js",
            "types": "./dist/index.d.ts"
        }
    },
    "scripts": {
        "build": "tsc",
        "dev": "tsc --watch"
    },
    "dependencies": {
        "zod": "^3.23.8"
    },
    "devDependencies": {
    }
}

```

### tsconfig.json
```
// packages/schemas/tsconfig.json
{
  "compilerOptions": {
    /* Visit https://aka.ms/tsconfig to read more about this file */

    /* Language and Environment */
    "target": "es2022",                                  /* Set the JavaScript language version for emitted JavaScript and include compatible library declarations. */

    /* Modules */
    "module": "NodeNext",
    "moduleResolution": "NodeNext",                                /* Specify what module code is generated. */
    "rootDir": "./src",                                  /* Specify the root folder within your source files. */

    /* Emitting Files */
    "declaration": true,                                 /* Generate .d.ts files from TypeScript and JavaScript files in your project. */
    "emitDeclarationOnly": false,                         /* Only output d.ts files and not JavaScript files. */
    "outDir": "./dist",                                  /* Specify an output folder for all emitted files. */

    /* Interop Constraints */
    "esModuleInterop": true,                             /* Emit additional JavaScript to ease support for importing CommonJS modules. This enables 'allowSyntheticDefaultImports' for type compatibility. */
    "forceConsistentCasingInFileNames": true,            /* Ensure that casing is correct in imports. */

    /* Type Checking */
    "strict": true,                                      /* Enable all strict type-checking options. */

    /* Completeness */
    "skipLibCheck": true                                 /* Skip type checking all .d.ts files. */
  },
  "include": ["src/**/*"], // 只编译 src 目录下的文件
  "exclude": ["node_modules", "dist"] // 排除这些目录
}
```

### dist/index.js
```
import { z } from 'zod';
// 使用 z.ZodType<ValueType> 显式注解，帮助 TS 理解递归结构。
export const ValueTypeSchema = z.lazy(() => z.discriminatedUnion('type', [
    z.object({ type: z.literal('string') }),
    z.object({ type: z.literal('number') }),
    z.object({ type: z.literal('boolean') }),
    z.object({ type: z.literal('any') }),
    z.object({
        type: z.literal('object'),
        properties: z.record(z.string(), ValueTypeSchema),
    }),
    z.object({
        type: z.literal('array'),
        item: ValueTypeSchema,
    }),
]));
// =================================================================
// 2. 所有独立的 Schema 定义
//    这部分是您项目的核心验证逻辑，它们本身是完全正确的。
// =================================================================
export const PortSchema = z.object({
    id: z.string().min(1),
    name: z.string(),
    valueType: ValueTypeSchema.default({ type: 'any' }),
    kind: z.enum(['data', 'control']).default('data'),
});
const BaseNodeSchema = z.object({
    id: z.string().min(1),
    name: z.string(),
    position: z.object({ x: z.number(), y: z.number() }),
});
export const LlmRuntimeSchema = z.object({
    type: z.literal('llm'),
    provider: z.enum(['openai', 'gemini']).default('gemini'),
    model: z.string().default('gemini-1.5-flash-latest'),
    systemPrompt: z.string().optional(),
    userPrompt: z.string(),
    temperature: z.number().min(0).max(2).default(0.7),
});
export const FunctionRuntimeSchema = z.object({
    type: z.literal('function'),
    functionName: z.string().min(1),
    inputSchema: z.record(z.string(), ValueTypeSchema).optional(),
    outputSchema: z.record(z.string(), ValueTypeSchema).optional(),
});
export const InputNodeSchema = BaseNodeSchema.extend({
    type: z.literal('input'),
    outputs: z.array(PortSchema),
});
export const OutputNodeSchema = BaseNodeSchema.extend({
    type: z.literal('output'),
    inputs: z.array(PortSchema),
});
export const ProcessorNodeSchema = BaseNodeSchema.extend({
    type: z.literal('processor'),
    inputs: z.array(PortSchema),
    outputs: z.array(PortSchema),
    runtime: z.discriminatedUnion('type', [
        LlmRuntimeSchema,
        FunctionRuntimeSchema,
    ]),
});
export const GraphNodeSchema = z.discriminatedUnion('type', [
    InputNodeSchema,
    OutputNodeSchema,
    ProcessorNodeSchema,
]);
export const EdgeSchema = z.object({
    id: z.string().min(1),
    sourceNodeId: z.string(),
    sourceOutputId: z.string(),
    targetNodeId: z.string(),
    targetInputId: z.string(),
});
// =================================================================
// 4. 定义最终的 Schema 和干净的输出 (Output) 类型
// =================================================================
// 定义最终的、唯一的 GraphSchema。
// 我们使用 z.lazy 来处理其内部的递归。
// 最关键的是，我们用 z.ZodType<GraphInput> 来注解它，这能完美通过类型检查，
// 因为 `GraphInput` 接口就是为它的输入形态量身定做的。
export const GraphSchema = z.lazy(() => z.object({
    id: z.string().min(1),
    name: z.string(),
    nodes: z.array(GraphNodeSchema),
    edges: z.array(EdgeSchema),
    variables: z.record(z.any()).optional(),
    subgraphs: z.record(z.string(), GraphSchema).optional(),
}));

```

### dist/index.d.ts
```
import { z } from 'zod';
type ValueType = {
    type: 'string';
} | {
    type: 'number';
} | {
    type: 'boolean';
} | {
    type: 'any';
} | {
    type: 'object';
    properties: Record<string, ValueType>;
} | {
    type: 'array';
    item: ValueType;
};
export declare const ValueTypeSchema: z.ZodType<ValueType>;
export declare const PortSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
    kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
}, "strip", z.ZodTypeAny, {
    id: string;
    name: string;
    valueType: ValueType;
    kind: "data" | "control";
}, {
    id: string;
    name: string;
    valueType?: ValueType | undefined;
    kind?: "data" | "control" | undefined;
}>;
export declare const LlmRuntimeSchema: z.ZodObject<{
    type: z.ZodLiteral<"llm">;
    provider: z.ZodDefault<z.ZodEnum<["openai", "gemini"]>>;
    model: z.ZodDefault<z.ZodString>;
    systemPrompt: z.ZodOptional<z.ZodString>;
    userPrompt: z.ZodString;
    temperature: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    type: "llm";
    provider: "openai" | "gemini";
    model: string;
    userPrompt: string;
    temperature: number;
    systemPrompt?: string | undefined;
}, {
    type: "llm";
    userPrompt: string;
    provider?: "openai" | "gemini" | undefined;
    model?: string | undefined;
    systemPrompt?: string | undefined;
    temperature?: number | undefined;
}>;
export declare const FunctionRuntimeSchema: z.ZodObject<{
    type: z.ZodLiteral<"function">;
    functionName: z.ZodString;
    inputSchema: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodType<ValueType, z.ZodTypeDef, ValueType>>>;
    outputSchema: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodType<ValueType, z.ZodTypeDef, ValueType>>>;
}, "strip", z.ZodTypeAny, {
    type: "function";
    functionName: string;
    inputSchema?: Record<string, ValueType> | undefined;
    outputSchema?: Record<string, ValueType> | undefined;
}, {
    type: "function";
    functionName: string;
    inputSchema?: Record<string, ValueType> | undefined;
    outputSchema?: Record<string, ValueType> | undefined;
}>;
export declare const InputNodeSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    position: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
} & {
    type: z.ZodLiteral<"input">;
    outputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    type: "input";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
}, {
    type: "input";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
}>;
export declare const OutputNodeSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    position: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
} & {
    type: z.ZodLiteral<"output">;
    inputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    type: "output";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    inputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
}, {
    type: "output";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    inputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
}>;
export declare const ProcessorNodeSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    position: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
} & {
    type: z.ZodLiteral<"processor">;
    inputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
    outputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
    runtime: z.ZodDiscriminatedUnion<"type", [z.ZodObject<{
        type: z.ZodLiteral<"llm">;
        provider: z.ZodDefault<z.ZodEnum<["openai", "gemini"]>>;
        model: z.ZodDefault<z.ZodString>;
        systemPrompt: z.ZodOptional<z.ZodString>;
        userPrompt: z.ZodString;
        temperature: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        type: "llm";
        provider: "openai" | "gemini";
        model: string;
        userPrompt: string;
        temperature: number;
        systemPrompt?: string | undefined;
    }, {
        type: "llm";
        userPrompt: string;
        provider?: "openai" | "gemini" | undefined;
        model?: string | undefined;
        systemPrompt?: string | undefined;
        temperature?: number | undefined;
    }>, z.ZodObject<{
        type: z.ZodLiteral<"function">;
        functionName: z.ZodString;
        inputSchema: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodType<ValueType, z.ZodTypeDef, ValueType>>>;
        outputSchema: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodType<ValueType, z.ZodTypeDef, ValueType>>>;
    }, "strip", z.ZodTypeAny, {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    }, {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    }>]>;
}, "strip", z.ZodTypeAny, {
    type: "processor";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
    inputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
    runtime: {
        type: "llm";
        provider: "openai" | "gemini";
        model: string;
        userPrompt: string;
        temperature: number;
        systemPrompt?: string | undefined;
    } | {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    };
}, {
    type: "processor";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
    inputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
    runtime: {
        type: "llm";
        userPrompt: string;
        provider?: "openai" | "gemini" | undefined;
        model?: string | undefined;
        systemPrompt?: string | undefined;
        temperature?: number | undefined;
    } | {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    };
}>;
export declare const GraphNodeSchema: z.ZodDiscriminatedUnion<"type", [z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    position: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
} & {
    type: z.ZodLiteral<"input">;
    outputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    type: "input";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
}, {
    type: "input";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
}>, z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    position: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
} & {
    type: z.ZodLiteral<"output">;
    inputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    type: "output";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    inputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
}, {
    type: "output";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    inputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
}>, z.ZodObject<{
    id: z.ZodString;
    name: z.ZodString;
    position: z.ZodObject<{
        x: z.ZodNumber;
        y: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        x: number;
        y: number;
    }, {
        x: number;
        y: number;
    }>;
} & {
    type: z.ZodLiteral<"processor">;
    inputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
    outputs: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodString;
        valueType: z.ZodDefault<z.ZodType<ValueType, z.ZodTypeDef, ValueType>>;
        kind: z.ZodDefault<z.ZodEnum<["data", "control"]>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }, {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }>, "many">;
    runtime: z.ZodDiscriminatedUnion<"type", [z.ZodObject<{
        type: z.ZodLiteral<"llm">;
        provider: z.ZodDefault<z.ZodEnum<["openai", "gemini"]>>;
        model: z.ZodDefault<z.ZodString>;
        systemPrompt: z.ZodOptional<z.ZodString>;
        userPrompt: z.ZodString;
        temperature: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        type: "llm";
        provider: "openai" | "gemini";
        model: string;
        userPrompt: string;
        temperature: number;
        systemPrompt?: string | undefined;
    }, {
        type: "llm";
        userPrompt: string;
        provider?: "openai" | "gemini" | undefined;
        model?: string | undefined;
        systemPrompt?: string | undefined;
        temperature?: number | undefined;
    }>, z.ZodObject<{
        type: z.ZodLiteral<"function">;
        functionName: z.ZodString;
        inputSchema: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodType<ValueType, z.ZodTypeDef, ValueType>>>;
        outputSchema: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodType<ValueType, z.ZodTypeDef, ValueType>>>;
    }, "strip", z.ZodTypeAny, {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    }, {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    }>]>;
}, "strip", z.ZodTypeAny, {
    type: "processor";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
    inputs: {
        id: string;
        name: string;
        valueType: ValueType;
        kind: "data" | "control";
    }[];
    runtime: {
        type: "llm";
        provider: "openai" | "gemini";
        model: string;
        userPrompt: string;
        temperature: number;
        systemPrompt?: string | undefined;
    } | {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    };
}, {
    type: "processor";
    id: string;
    name: string;
    position: {
        x: number;
        y: number;
    };
    outputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
    inputs: {
        id: string;
        name: string;
        valueType?: ValueType | undefined;
        kind?: "data" | "control" | undefined;
    }[];
    runtime: {
        type: "llm";
        userPrompt: string;
        provider?: "openai" | "gemini" | undefined;
        model?: string | undefined;
        systemPrompt?: string | undefined;
        temperature?: number | undefined;
    } | {
        type: "function";
        functionName: string;
        inputSchema?: Record<string, ValueType> | undefined;
        outputSchema?: Record<string, ValueType> | undefined;
    };
}>]>;
export declare const EdgeSchema: z.ZodObject<{
    id: z.ZodString;
    sourceNodeId: z.ZodString;
    sourceOutputId: z.ZodString;
    targetNodeId: z.ZodString;
    targetInputId: z.ZodString;
}, "strip", z.ZodTypeAny, {
    id: string;
    sourceNodeId: string;
    sourceOutputId: string;
    targetNodeId: string;
    targetInputId: string;
}, {
    id: string;
    sourceNodeId: string;
    sourceOutputId: string;
    targetNodeId: string;
    targetInputId: string;
}>;
type NodeInput = z.input<typeof GraphNodeSchema>;
type EdgeInput = z.input<typeof EdgeSchema>;
interface GraphInput {
    id: string;
    name: string;
    nodes: NodeInput[];
    edges: EdgeInput[];
    variables?: Record<string, any>;
    subgraphs?: Record<string, GraphInput>;
}
export declare const GraphSchema: z.ZodType<GraphInput>;
export type Graph = z.infer<typeof GraphSchema>;
export type Port = z.infer<typeof PortSchema>;
export type LlmRuntime = z.infer<typeof LlmRuntimeSchema>;
export type FunctionRuntime = z.infer<typeof FunctionRuntimeSchema>;
export type InputNode = z.infer<typeof InputNodeSchema>;
export type OutputNode = z.infer<typeof OutputNodeSchema>;
export type ProcessorNode = z.infer<typeof ProcessorNodeSchema>;
export type GraphNode = z.infer<typeof GraphNodeSchema>;
export type Edge = z.infer<typeof EdgeSchema>;
export type { GraphInput };

```

### src/index.ts
```
import { z, ZodTypeAny } from 'zod';

// =================================================================
// 1. 元类型定义 (Meta-Schema)
// =================================================================

type ValueType =
  | { type: 'string' }
  | { type: 'number' }
  | { type: 'boolean' }
  | { type: 'any' }
  | { type: 'object'; properties: Record<string, ValueType> }
  | { type: 'array'; item: ValueType };

export const ValueTypeSchema: z.ZodType<ValueType> = z.lazy(() =>
  z.discriminatedUnion('type', [
    z.object({ type: z.literal('string') }),
    z.object({ type: z.literal('number') }),
    z.object({ type: z.literal('boolean') }),
    z.object({ type: z.literal('any') }),
    z.object({
      type: 'object',
      properties: z.record(z.string(), ValueTypeSchema),
    }),
    z.object({
      type: 'array',
      item: ValueTypeSchema,
    }),
  ])
);

// =================================================================
// 2. 所有 Schema 定义
// =================================================================

export const PortSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  valueType: ValueTypeSchema.default({ type: 'any' }),
  kind: z.enum(['data', 'control']).default('data'),
});

const BaseNodeSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  position: z.object({ x: z.number(), y: z.number() }),
});

export const LlmRuntimeSchema = z.object({
  type: z.literal('llm'),
  provider: z.enum(['openai', 'gemini']).default('gemini'),
  model: z.string().default('gemini-1.5-flash-latest'),
  systemPrompt: z.string().optional(),
  userPrompt: z.string(),
  temperature: z.number().min(0).max(2).default(0.7),
});

export const FunctionRuntimeSchema = z.object({
  type: z.literal('function'),
  functionName: z.string().min(1),
  inputSchema: z.record(z.string(), ValueTypeSchema).optional(),
  outputSchema: z.record(z.string(), ValueTypeSchema).optional(),
});

export const InputNodeSchema = BaseNodeSchema.extend({
  type: z.literal('input'),
  outputs: z.array(PortSchema),
});

export const OutputNodeSchema = BaseNodeSchema.extend({
  type: z.literal('output'),
  inputs: z.array(PortSchema),
});

export const ProcessorNodeSchema = BaseNodeSchema.extend({
  type: z.literal('processor'),
  inputs: z.array(PortSchema),
  outputs: z.array(PortSchema),
  runtime: z.discriminatedUnion('type', [
    LlmRuntimeSchema,
    FunctionRuntimeSchema,
  ]),
});

export const GraphNodeSchema = z.discriminatedUnion('type', [
  InputNodeSchema,
  OutputNodeSchema,
  ProcessorNodeSchema,
]);

export const EdgeSchema = z.object({
  id: z.string().min(1),
  sourceNodeId: z.string(),
  sourceOutputId: z.string(),
  targetNodeId: z.string(),
  targetInputId: z.string(),
});

// =================================================================
// 3. 递归的 Graph 定义 (最终解决方案)
// =================================================================

interface GraphInput {
  id: string;
  name: string;
  nodes: z.input<typeof GraphNodeSchema>[];
  edges: z.input<typeof EdgeSchema>[];
  variables?: Record<string, any>;
  subgraphs?: Record<string, GraphInput>;
}

export const GraphSchema: z.ZodType<GraphInput> = z.lazy(() =>
  z.object({
    id: z.string().min(1),
    name: z.string(),
    nodes: z.array(GraphNodeSchema),
    edges: z.array(EdgeSchema),
    variables: z.record(z.any()).optional(),
    subgraphs: z.record(z.string(), GraphSchema).optional(),
  })
);

// =================================================================
// 4. 导出所有推断出的 *输出* 类型 (供应用层使用)
// =================================================================

export type Graph = z.infer<typeof GraphSchema>;
export type Port = z.infer<typeof PortSchema>;
export type LlmRuntime = z.infer<typeof LlmRuntimeSchema>;
export type FunctionRuntime = z.infer<typeof FunctionRuntimeSchema>;
export type InputNode = z.infer<typeof InputNodeSchema>;
export type OutputNode = z.infer<typeof OutputNodeSchema>;
export type ProcessorNode = z.infer<typeof ProcessorNodeSchema>;
export type GraphNode = z.infer<typeof GraphNodeSchema>;
export type Edge = z.infer<typeof EdgeSchema>;
export type { ValueType, GraphInput };

// =================================================================
// 5. 类型解释器/验证器构建函数。提供了将类型定义转换为运行时验证的能力。
// =================================================================

/**
 * 递归地将 ValueType 对象构建成一个可执行的 Zod 验证器。
 * @param valueType - 一个 ValueType 定义对象。
 * @returns 一个 ZodType，可以用来 .parse() 数据。
 */
export function buildZodValidatorFromValueType(valueType: ValueType): ZodTypeAny {
  switch (valueType.type) {
    case 'string':
      return z.string();
    case 'number':
      return z.number();
    case 'boolean':
      return z.boolean();
    case 'any':
      return z.any();
    case 'object':
      const shape: Record<string, ZodTypeAny> = {};
      for (const key in valueType.properties) {
        // 确保我们只处理对象自身的属性，而不是原型链上的
        if (Object.prototype.hasOwnProperty.call(valueType.properties, key)) {
          shape[key] = buildZodValidatorFromValueType(valueType.properties[key]);
        }
      }
      return z.object(shape);
    case 'array':
      const itemValidator = buildZodValidatorFromValueType(valueType.item);
      return z.array(itemValidator);
    default:
      // 这个 `exhaustiveCheck` 确保了如果我们向 `ValueType` 联合类型中添加了新的类型，
      // 而忘记在这里的 switch-case 中处理它，TypeScript 会在编译时报错。
      // 这是一种强大的类型安全编程模式。
      const exhaustiveCheck: never = valueType;
      throw new Error(`Unhandled ValueType: ${JSON.stringify(exhaustiveCheck)}`);
  }
}

/**
 * 为函数输入/输出的整个对象构建一个 Zod 验证器。
 * @param schema - `Record<string, ValueType>` 格式的 schema，例如 `FunctionRuntime.inputSchema`。
 * @returns 一个 `z.object({...})` 验证器。
 */
export function buildObjectValidatorFromSchema(
  schema: Record<string, ValueType>
): z.ZodObject<Record<string, ZodTypeAny>> {
  const shape: Record<string, ZodTypeAny> = {};
  for (const key in schema) {
    if (Object.prototype.hasOwnProperty.call(schema, key)) {
      shape[key] = buildZodValidatorFromValueType(schema[key]);
    }
  }
  // 使用 .passthrough() 允许对象包含 schema 中未定义的其他属性。
  // 这在处理节点输入时通常更灵活，因为节点可能接收到上游传来的、但并非自己必需的额外数据。
  // 如果需要严格匹配，可以使用 `z.object(shape)` 或 `z.strictObject(shape)`。
  return z.object(shape).passthrough();
}
```
