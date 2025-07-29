import { Graph, GraphNode } from '@hevno/schemas';
import { topologicalSort } from './graph';
import { ExecutionContext, INodeRunner } from './types';
import { FunctionRunner } from './runners/FunctionRunner';

export class GraphExecutor {
  private nodeRunners: Map<string, INodeRunner>;

  constructor() {
    this.nodeRunners = new Map();
    // 注册已有的执行器
    this.nodeRunners.set('function', new FunctionRunner());
    // 未来会添加: this.nodeRunners.set('llm', new LlmRunner());
  }

  public async execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext> {
    const sortedNodeIds = topologicalSort(graph.nodes, graph.edges);
    const context: ExecutionContext = { outputs: {} };

    // 初始化输入节点
    const inputNodes = graph.nodes.filter(n => n.type === 'input');
    for (const inputNode of inputNodes) {
        if (initialInputs[inputNode.id]) {
            context.outputs[inputNode.id] = initialInputs[inputNode.id];
        }
    }

    for (const nodeId of sortedNodeIds) {
      const node = graph.nodes.find(n => n.id === nodeId);
      if (!node || node.type === 'input') continue; // 跳过输入节点

      // 1. 收集当前节点的输入
      const nodeInputs: Record<string, any> = {};
      const incomingEdges = graph.edges.filter(e => e.targetNodeId === nodeId);
      for (const edge of incomingEdges) {
        const sourceOutput = context.outputs[edge.sourceNodeId]?.[edge.sourceOutputId];
        nodeInputs[edge.targetInputId] = sourceOutput;
      }
      
      console.log(`Executing node ${node.name} (${node.id}) with inputs:`, nodeInputs);

      // 2. 找到并运行对应的执行器
      if (node.type === 'processor') {
        const runner = this.nodeRunners.get(node.runtime.type);
        if (runner) {
          const result = await runner.run(node, nodeInputs);
          context.outputs[node.id] = result;
          console.log(`Node ${node.id} produced output:`, result);
        } else {
            console.warn(`No runner found for processor type: ${node.runtime.type}`);
        }
      } else if (node.type === 'output') {
          // 输出节点通常只传递数据
          context.outputs[node.id] = nodeInputs;
      }

      // 可以在这里通过事件发射器或回调来通知外部执行进度
    }

    return context;
  }
}