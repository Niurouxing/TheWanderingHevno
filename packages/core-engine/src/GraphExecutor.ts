// packages/core-engine/src/GraphExecutor.ts
import { Graph, GraphNode, ProcessorNode } from '@hevno/schemas';
import { topologicalSort } from './graph';
import { ExecutionContext, INodeRunner, CoreServices } from './types';
import { LlmRunner } from './runners/LlmRunner';
import { FunctionRunner } from './runners/FunctionRunner';
import { resolveTemplate } from './TemplateResolver';

export class GraphExecutor {
  private runners: Map<string, INodeRunner>;
  private services: CoreServices;

  constructor() {
    this.runners = new Map();
    this.runners.set('llm', new LlmRunner());
    this.runners.set('function', new FunctionRunner());

    // 实例化 CoreServices，并传入自身
    this.services = {
      graphExecutor: this,
      graphRegistry: new Map<string, Graph>(),
    };
  }
  
  /**
   * 注册子图，以便 `core:runGraph` 函数可以找到它们。
   */
  private registerSubgraphs(graph: Graph) {
      if (graph.subgraphs) {
          for (const graphId in graph.subgraphs) {
              this.services.graphRegistry.set(graphId, graph.subgraphs[graphId]);
          }
      }
  }

  public async execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext> {
    this.registerSubgraphs(graph);
    
    const sortedNodeIds = topologicalSort(graph.nodes, graph.edges);
    const context: ExecutionContext = {
      outputs: {},
      variables: JSON.parse(JSON.stringify(graph.variables || {})), // Deep copy
    };

    // 初始化输入节点的输出
    const inputNodes = graph.nodes.filter(n => n.type === 'input');
    for (const inputNode of inputNodes) {
      context.outputs[inputNode.id] = initialInputs[inputNode.id] || {};
    }

    for (const nodeId of sortedNodeIds) {
      const node = graph.nodes.find(n => n.id === nodeId);
      if (!node || node.type === 'input') continue;

      console.log(`[Executor] Processing node: ${node.name} (${node.id})`);

      // 1. 收集当前节点的输入
      const nodeInputs: Record<string, any> = {};
      const incomingEdges = graph.edges.filter(e => e.targetNodeId === nodeId);
      for (const edge of incomingEdges) {
        // 只有 'data' 类型的边才传递数据
        const sourcePort = graph.nodes.find(n => n.id === edge.sourceNodeId)?.outputs.find(p => p.id === edge.sourceOutputId);
        if (sourcePort?.kind === 'data') {
            const sourceValue = context.outputs[edge.sourceNodeId]?.[edge.sourceOutputId];
            nodeInputs[edge.targetInputId] = sourceValue;
        }
      }
      
      // 2. 执行节点逻辑
      if (node.type === 'processor') {
        // 对节点的运行时配置也进行模板解析
        const resolvedRuntime = resolveTemplate(node.runtime, context);
        const resolvedNode = { ...node, runtime: resolvedRuntime };

        const runner = this.runners.get(resolvedNode.runtime.type);
        if (runner) {
          const result = await runner.run(resolvedNode, nodeInputs, context, this.services);
          context.outputs[node.id] = result;
          console.log(`[Executor] Node ${node.id} produced output:`, result);
        } else {
          console.warn(`No runner found for processor type: ${resolvedNode.runtime.type}`);
        }
      } else if (node.type === 'output') {
        context.outputs[node.id] = nodeInputs;
      }
    }

    return context;
  }
}