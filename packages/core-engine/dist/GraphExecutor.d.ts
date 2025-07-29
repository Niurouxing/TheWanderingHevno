import { Graph } from '@hevno/schemas';
import { ExecutionContext, IGraphExecutor } from './types';
export declare class GraphExecutor implements IGraphExecutor {
    private runners;
    private services;
    private functionRegistry;
    constructor();
    registerFunction(name: string, func: any): void;
    private getRunner;
    private validateGraphConnections;
    private registerSubgraphs;
    execute(graph: Graph, initialInputs: Record<string, any>): Promise<ExecutionContext>;
}
