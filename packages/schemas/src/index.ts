// packages/schemas/src/index.ts
import { z } from 'zod';

// =================================================================
// 1. 基础构成元素 (Primitives)
// =================================================================

/**
 * 定义节点的输入/输出端口。
 * 'kind' 字段是关键，它区分了数据流和控制流。
 */
export const PortSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  type: z.string().default('any'), // e.g., 'string', 'number', 'object' for type hints
  kind: z.enum(['data', 'control']).default('data'),
});
export type Port = z.infer<typeof PortSchema>;

/**
 * 基础节点，定义所有节点的共同属性，如 ID 和在 UI 上的位置。
 */
const BaseNodeSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  position: z.object({ x: z.number(), y: z.number() }),
});

// =================================================================
// 2. 处理器节点运行时配置 (Processor Runtimes)
// 这是整个系统的核心，定义了 Processor 节点能做什么。
// =================================================================

/**
 * LLM 节点运行时配置。
 * `userPrompt` 是一个模板字符串，可以引用其他节点的输出。
 */
export const LlmRuntimeSchema = z.object({
  type: z.literal('llm'),
  provider: z.enum(['openai', 'gemini']).default('gemini'),
  model: z.string().default('gemini-2.5-flash'),
  systemPrompt: z.string().optional(),
  userPrompt: z.string(),
  temperature: z.number().min(0).max(2).default(0.7),
});
export type LlmRuntime = z.infer<typeof LlmRuntimeSchema>;

/**
 * 函数节点运行时配置。
 * `functionName` 对应函数注册表中的键。
 * `config` 对象允许向函数传递静态配置参数，如子图调用的 `graphId`。
 */
export const FunctionRuntimeSchema = z.object({
  type: z.literal('function'),
  functionName: z.string().min(1),
  config: z.record(z.any()).optional(),
});
export type FunctionRuntime = z.infer<typeof FunctionRuntimeSchema>;

// =================================================================
// 3. 极简的节点类型定义 (Node Types)
// =================================================================

/**
 * 输入节点：图的入口。
 * 定义了图启动时可以接受哪些数据。
 */
export const InputNodeSchema = BaseNodeSchema.extend({
  type: z.literal('input'),
  outputs: z.array(PortSchema),
});
export type InputNode = z.infer<typeof InputNodeSchema>;

/**
 * 输出节点：图的出口。
 * 定义了图执行完毕后，对外暴露哪些结果。
 */
export const OutputNodeSchema = BaseNodeSchema.extend({
  type: z.literal('output'),
  inputs: z.array(PortSchema),
});
export type OutputNode = z.infer<typeof OutputNodeSchema>;

/**
 * 处理器节点：唯一的“工作马”。
 * 它的具体行为由 `runtime` 配置决定，可以是 LLM 调用或函数执行。
 */
export const ProcessorNodeSchema = BaseNodeSchema.extend({
  type: z.literal('processor'),
  inputs: z.array(PortSchema),
  outputs: z.array(PortSchema),
  runtime: z.discriminatedUnion('type', [
    LlmRuntimeSchema,
    FunctionRuntimeSchema,
  ]),
});
export type ProcessorNode = z.infer<typeof ProcessorNodeSchema>;

/**

 * 所有可能的节点类型的联合体。
 * 保持极简，易于管理。
 */
export const GraphNodeSchema = z.discriminatedUnion('type', [
  InputNodeSchema,
  OutputNodeSchema,
  ProcessorNodeSchema,
]);
export type GraphNode = z.infer<typeof GraphNodeSchema>;


// =================================================================
// 4. 图与边 (Graph & Edge)
// =================================================================

/**
 * 定义了节点之间的连接。
 * 精确到端口级别。
 */
export const EdgeSchema = z.object({
  id: z.string().min(1),
  sourceNodeId: z.string(),
  sourceOutputId: z.string(),
  targetNodeId: z.string(),
  targetInputId: z.string(),
});
export type Edge = z.infer<typeof EdgeSchema>;

/**
 * 图的完整定义。
 * 包含节点、边，以及可选的全局变量和子图定义。
 */
export const GraphSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  nodes: z.array(GraphNodeSchema),
  edges: z.array(EdgeSchema),
  variables: z.record(z.any()).optional(),
  // 子图定义，键是 graphId，值是另一个 GraphSchema。
  // 使用 z.lazy 来处理递归定义。
  subgraphs: z.lazy(() => z.record(z.string(), GraphSchema)).optional(),
});
export type Graph = z.infer<typeof GraphSchema>;