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
    // [修正] 确保判别字段 'type' 的值是一个 z.literal Schema
    z.object({
      type: z.literal('object'),
      properties: z.record(z.string(), ValueTypeSchema),
    }),
    // [修正] 确保判别字段 'type' 的值是一个 z.literal Schema
    z.object({
      type: z.literal('array'),
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
// 3. 递归的 Graph 定义
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
// 4. 导出所有推断出的 *输出* 类型
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
// 5. 类型解释器/验证器构建函数
// =================================================================
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
        if (Object.prototype.hasOwnProperty.call(valueType.properties, key)) {
          shape[key] = buildZodValidatorFromValueType(valueType.properties[key]);
        }
      }
      return z.object(shape);
    case 'array':
      const itemValidator = buildZodValidatorFromValueType(valueType.item);
      return z.array(itemValidator);
    default:
      const exhaustiveCheck: never = valueType;
      throw new Error(`Unhandled ValueType: ${JSON.stringify(exhaustiveCheck)}`);
  }
}

export function buildObjectValidatorFromSchema(
  schema: Record<string, ValueType>
): z.ZodObject<Record<string, ZodTypeAny>> {
  const shape: Record<string, ZodTypeAny> = {};
  for (const key in schema) {
    if (Object.prototype.hasOwnProperty.call(schema, key)) {
      shape[key] = buildZodValidatorFromValueType(schema[key]);
    }
  }
  return z.object(shape).passthrough();
}