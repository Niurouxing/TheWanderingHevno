import { z, ZodTypeAny } from 'zod';
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
interface GraphInput {
    id: string;
    name: string;
    nodes: z.input<typeof GraphNodeSchema>[];
    edges: z.input<typeof EdgeSchema>[];
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
export type { ValueType, GraphInput };
export declare function buildZodValidatorFromValueType(valueType: ValueType): ZodTypeAny;
export declare function buildObjectValidatorFromSchema(schema: Record<string, ValueType>): z.ZodObject<Record<string, ZodTypeAny>>;
