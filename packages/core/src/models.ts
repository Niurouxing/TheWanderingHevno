import { z } from 'zod';

// =================================================================
// 基础构建块：端口和边
// =================================================================

/**
 * 定义节点的输入端口
 */
export const InputPortSchema = z.object({
  id: z.string(), // e.g., "prompt", "context", "tools"
  name: z.string(),
  type: z.string().default('any'), // 可选，用于类型检查 e.g., "string", "number[]"
});
export type InputPort = z.infer<typeof InputPortSchema>;

/**
 * 定义节点的输出端口
 */
export const OutputPortSchema = z.object({
  id: z.string(), // e.g., "output", "result", "error"
  name: z.string(),
  type: z.string().default('any'),
});
export type OutputPort = z.infer<typeof OutputPortSchema>;


/**
 * 定义连接两个节点端口的边
 */
export const EdgeSchema = z.object({
  id: z.string(),
  sourceNodeId: z.string(),
  sourceOutputId: z.string(),
  targetNodeId: z.string(),
  targetInputId: z.string(),
});
export type Edge = z.infer<typeof EdgeSchema>;


// =================================================================
// 基础节点类型
// =================================================================

const BaseNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(), // 节点类型，将用于区分联合类型
  position: z.object({ x: z.number(), y: z.number() }).default({ x: 0, y: 0 }), // 用于前端可视化
  // 输入输出端口由用户在创建时自定义，因此不再提供默认值
  inputs: z.array(InputPortSchema),
  outputs: z.array(OutputPortSchema),
});


// =================================================================
// 特定节点类型定义
// =================================================================

/**
 * 输入节点：作为图的起点，接收外部数据
 */
export const InputNodeSchema = BaseNodeSchema.extend({
  type: z.literal('input'),
  outputs: z.array(OutputPortSchema).default([{ id: 'output', name: 'Output' }]),
});
export type InputNode = z.infer<typeof InputNodeSchema>;

/**
 * 输出节点：作为图的终点，汇集最终结果
 */
export const OutputNodeSchema = BaseNodeSchema.extend({
  type: z.literal('output'),
  inputs: z.array(InputPortSchema).default([{ id: 'input', name: 'Input' }]),
});
export type OutputNode = z.infer<typeof OutputNodeSchema>;


/**
 * 新增：通用的处理器节点 (ProcessorNode)
 * 它将取代 LlmNode, FunctionNode, JoinNode 等
 */

const LlmRuntimeSchema = z.object({
    type: z.literal('llm'),
    provider: z.string(),
    model: z.string(),
    temperature: z.number().min(0).max(2).default(0.7),
    // prompt模板现在将通过一个自定义的输入端口传入，而不是固定字段
});

const FunctionRuntimeSchema = z.object({
    type: z.literal('function'),
    functionName: z.string(),
});

export const ProcessorNodeSchema = BaseNodeSchema.extend({
    type: z.literal('processor'),
    // 节点的具体行为由 runtime 定义
    runtime: z.discriminatedUnion('type', [
        LlmRuntimeSchema,
        FunctionRuntimeSchema,
    ]),
});
export type ProcessorNode = z.infer<typeof ProcessorNodeSchema>;


/**
 * 结构节点：MapNode
 * 它的职责是流程控制，因此保持独立
 */
export const MapNodeSchema = BaseNodeSchema.extend({
  type: z.literal('map'),
  // The subgraph to be executed for each item in the input list.
  subgraph: z.lazy(() => GraphSchema),
  // 端口是固定的，因为它有明确的结构化功能
  inputs: z.array(InputPortSchema).default([{ id: 'list', name: 'List' }]),
  outputs: z.array(OutputPortSchema).default([{ id: 'results', name: 'Results' }]),
});
export type MapNode = z.infer<typeof MapNodeSchema>;


/**
 * 结构节点：RouterNode
 * 它的职责是流程控制，因此保持独立
 */
export const RouterNodeSchema = BaseNodeSchema.extend({
  type: z.literal('router'),
  // 路由逻辑将由连接到不同输出端口的边来决定
  inputs: z.array(InputPortSchema).default([{ id: 'condition', name: 'Condition' }]),
  // 输出端口代表不同的路由分支，用户可以自定义这些分支
  outputs: z.array(OutputPortSchema),
});
export type RouterNode = z.infer<typeof RouterNodeSchema>;


// =================================================================
// 联合节点类型 (Discriminated Union)
// =================================================================

export const GraphNodeSchema = z.discriminatedUnion('type', [
  InputNodeSchema,
  OutputNodeSchema,
  ProcessorNodeSchema, // 统一的处理器节点
  MapNodeSchema,
  RouterNodeSchema,
]);
export type GraphNode = z.infer<typeof GraphNodeSchema>;


// =================================================================
// 完整图（Graph）定义
// =================================================================

export const GraphSchema = z.object({
    id: z.string(),
    name: z.string(),
    nodes: z.array(GraphNodeSchema),
    edges: z.array(EdgeSchema),
});
export type Graph = z.infer<typeof GraphSchema>;
