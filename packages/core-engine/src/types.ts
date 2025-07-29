// packages/core-engine/src/types.ts
import { Graph, GraphNode, ProcessorNode } from '@hevno/schemas';
import { GraphExecutor } from './GraphExecutor';

/**
 * 执行上下文，贯穿整个图的执行过程。
 * 包含所有已执行节点的输出和全局变量。
 */
export type ExecutionContext = {
  outputs: Record<string, Record<string, any>>;
  variables: Record<string, any>;
};

/**
 * 传递给核心函数和 Runner 的服务集合。
 * 用于提供像图执行器、图注册表等系统级能力，避免循环依赖。
 */
export type CoreServices = {
  graphExecutor: GraphExecutor;
  graphRegistry: Map<string, Graph>;
  // 未来可以添加数据库服务、文件系统服务等
};

/**
 * 节点执行器的接口。
 * Processor 节点的每种 runtime 类型都有一个对应的 Runner。
 */
export interface INodeRunner {
  run(
    node: ProcessorNode,
    inputs: Record<string, any>,
    context: ExecutionContext,
    services: CoreServices
  ): Promise<Record<string, any>>;
}