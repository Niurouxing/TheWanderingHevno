// packages/core-engine/src/GraphExecutor.ts
import { Graph, GraphNode, ProcessorNode, ValueType } from '@hevno/schemas';
import { topologicalSort } from './graph';
import { ExecutionContext, INodeRunner, CoreServices, IGraphExecutor } from './types';
import { LlmRunner } from './runners/LlmRunner';
import { FunctionRunner } from './runners/FunctionRunner';
import { resolveTemplate } from './TemplateResolver';


function areTypesCompatible(sourceType: ValueType, targetType: ValueType): boolean {
    if (targetType.type === 'any' || sourceType.type === 'any') {
        return true;
    }
    return sourceType.type === targetType.type;
}

// 注意：我们让 GraphExecutor 实现 IGraphExecutor 接口，这是一个好习惯
export class GraphExecutor implements IGraphExecutor {
  private runners: Map<string, INodeRunner>;
  private services: CoreServices;
  private functionRegistry: Map<string, any>;

  constructor() {
    // *** 修改点 1: 构造函数变得非常简单 ***
    // 不再立即创建 Runner 实例。只初始化容器。
    this.runners = new Map();
    this.functionRegistry = new Map();

    // CoreServices 的创建是安全的，因为它只引用 `this`
    this.services = {
      graphExecutor: this,
      graphRegistry: new Map<string, Graph>(),
    };
  }

  // 提供一个方法来从外部注册自定义函数
  public registerFunction(name: string, func: any) {
    this.functionRegistry.set(name, func);
  }

  // *** 修改点 2: 添加一个私有的 getRunner 方法 ***
  private getRunner(type: string): INodeRunner | undefined {
    // 如果已经创建过，直接返回
    if (this.runners.has(type)) {
      return this.runners.get(type);
    }

    // 如果没有，现在才按需创建（懒加载）
    let runner: INodeRunner | undefined;
    if (type === 'llm') {
      runner = new LlmRunner();
    } else if (type === 'function') {
      // 确保 FunctionRunner 在创建时，它的核心函数已经注册
      runner = new FunctionRunner(this.functionRegistry);
    }

    if (runner) {
      this.runners.set(type, runner);
    }
    
    return runner;
  }

   private validateGraphConnections(graph: Graph) {
    console.log("[Executor] Validating graph connections...");
    for (const edge of graph.edges) {
      const sourceNode = graph.nodes.find(n => n.id === edge.sourceNodeId);
      const targetNode = graph.nodes.find(n => n.id === edge.targetNodeId);
      if (!sourceNode || !targetNode) continue;
      const sourcePort = sourceNode.outputs.find(p => p.id === edge.sourceOutputId);
      const targetPort = targetNode.inputs.find(p => p.id === edge.targetInputId);
      if (!sourcePort || !targetPort) {
        throw new Error(`Edge ${edge.id} connects to a non-existent port.`);
      }
      if (sourcePort.kind === 'data' && targetPort.kind === 'data') {
         if (!areTypesCompatible(sourcePort.valueType, targetPort.valueType)) {
            console.warn(
              `Type mismatch on edge ${edge.id}: ` +
              `Source "${sourceNode.name}.${sourcePort.name}" (${JSON.stringify(sourcePort.valueType)}) ` +
              `is not compatible with Target "${targetNode.name}.${targetPort.name}" (${JSON.stringify(targetPort.valueType)}).`
            );
         }
      }
    }
    console.log("[Executor] Graph connections validated.");
  }
  
  private registerSubgraphs(graph: Graph) {
      if (graph.subgraphs) {
          for (const graphId in graph.subgraphs) {
              this.services.graphRegistry.set(graphId, graph.subgraphs[graphId]);
          }
      }
  }

  public async execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext> {
    this.validateGraphConnections(graph);
    this.registerSubgraphs(graph);
    
    const sortedNodeIds = topologicalSort(graph.nodes, graph.edges);
    const context: ExecutionContext = {
      outputs: {},
      variables: JSON.parse(JSON.stringify(graph.variables || {})),
    };

    const inputNodes = graph.nodes.filter(n => n.type === 'input');
    for (const inputNode of inputNodes) {
      context.outputs[inputNode.id] = initialInputs[inputNode.id] || {};
    }

    for (const nodeId of sortedNodeIds) {
      const node = graph.nodes.find(n => n.id === nodeId);
      if (!node || node.type === 'input') continue;

      console.log(`[Executor] Processing node: ${node.name} (${node.id})`);

      const nodeInputs: Record<string, any> = {};
      const incomingEdges = graph.edges.filter(e => e.targetNodeId === nodeId);
      for (const edge of incomingEdges) {
        const sourcePort = graph.nodes.find(n => n.id === edge.sourceNodeId)?.outputs.find(p => p.id === edge.sourceOutputId);
        if (sourcePort?.kind === 'data') {
            const sourceValue = context.outputs[edge.sourceNodeId]?.[edge.sourceOutputId];
            nodeInputs[edge.targetInputId] = sourceValue;
        }
      }
      
      if (node.type === 'processor') {
        const resolvedRuntime = resolveTemplate(node.runtime, context);
        const resolvedNode = { ...node, runtime: resolvedRuntime };

        // *** 修改点 3: 使用 getRunner 方法 ***
        const runner = this.getRunner(resolvedNode.runtime.type);
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