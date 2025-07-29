import { Graph, ProcessorNode } from '@hevno/schemas';
/**
 * 这是我们将要创建的接口，用于打破循环依赖
 */
export interface IGraphExecutor {
    execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext>;
}
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
    graphExecutor: IGraphExecutor;
    graphRegistry: Map<string, Graph>;
};
/**
 * 节点执行器的接口。
 * Processor 节点的每种 runtime 类型都有一个对应的 Runner。
 */
export interface INodeRunner {
    run(node: ProcessorNode, inputs: Record<string, any>, context: ExecutionContext, services: CoreServices): Promise<Record<string, any>>;
}
