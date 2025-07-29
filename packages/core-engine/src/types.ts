import { GraphNode } from '@hevno/schemas';

// 执行上下文，包含所有节点的输出状态
export type ExecutionContext = {
  // {[nodeId]: {[outputId]: value}}
  outputs: Record<string, Record<string, any>>;
};

// 节点执行器的接口
export interface INodeRunner {
  // 接受节点定义和当前所有上游节点的输入值
  run(node: GraphNode, inputs: Record<string, any>): Promise<Record<string, any>>;
}