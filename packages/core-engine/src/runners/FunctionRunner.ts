// packages/core-engine/src/runners/FunctionRunner.ts
import { ProcessorNode } from '@hevno/schemas';
import { INodeRunner, ExecutionContext, CoreServices } from '../types';
import { resolveTemplate } from '../TemplateResolver';

type AnyFunction = (inputs: any, context: ExecutionContext, services: CoreServices) => any;

// === 函数注册表 ===
const functionRegistry = new Map<string, AnyFunction>();

// --- 核心“元能力”函数 ---
functionRegistry.set('core:setVariable', (inputs, context) => {
  if (context.variables && inputs.name) {
    context.variables[inputs.name] = inputs.value;
  }
  return {}; // 纯副作用，无数据输出
});

functionRegistry.set('core:getVariable', (inputs, context) => {
  const value = context.variables ? context.variables[inputs.name] : undefined;
  return { value };
});

functionRegistry.set('core:runGraph', async (inputs, context, services) => {
  const { graphExecutor, graphRegistry } = services;
  const { graphId, ...subgraphInputs } = inputs;

  if (!graphId || typeof graphId !== 'string') {
    throw new Error('`graphId` must be provided and be a string to `core:runGraph`.');
  }

  const subgraph = graphRegistry.get(graphId);
  if (!subgraph) {
    throw new Error(`Subgraph with id "${graphId}" not found in registry.`);
  }

  // 子图的输入节点通常只有一个，ID 默认为 'input'
  const subgraphInputNodes = subgraph.nodes.filter(n => n.type === 'input');
  if (subgraphInputNodes.length !== 1) {
      throw new Error(`Subgraph "${graphId}" must have exactly one Input node.`);
  }
  const inputNodeId = subgraphInputNodes[0].id;

  const resultContext = await graphExecutor.execute(subgraph, { [inputNodeId]: subgraphInputs });
  
  // 子图的输出节点通常也只有一个，ID 默认为 'output'
  const subgraphOutputNodes = subgraph.nodes.filter(n => n.type === 'output');
   if (subgraphOutputNodes.length !== 1) {
      throw new Error(`Subgraph "${graphId}" must have exactly one Output node.`);
  }
  const outputNodeId = subgraphOutputNodes[0].id;
  
  // 返回整个输出节点的输入对象
  return resultContext.outputs[outputNodeId] || {};
});

// --- 用户自定义函数示例 ---
functionRegistry.set('custom:add', (inputs) => ({ result: inputs.a + inputs.b }));
functionRegistry.set('custom:concatenate', (inputs) => ({ result: `${inputs.str1}${inputs.str2}` }));

export class FunctionRunner implements INodeRunner {
  async run(
    node: ProcessorNode,
    inputs: Record<string, any>,
    context: ExecutionContext,
    services: CoreServices
  ): Promise<Record<string, any>> {
    if (node.runtime.type !== 'function') {
      throw new Error('Invalid node type for FunctionRunner');
    }

    const { functionName, config } = node.runtime;
    const func = functionRegistry.get(functionName);
    if (!func) {
      throw new Error(`Function "${functionName}" not found in registry.`);
    }

    // 将节点的动态输入和静态配置合并后传递给函数
    const allInputs = { ...inputs, ...config };

    return Promise.resolve(func(allInputs, context, services));
  }
}