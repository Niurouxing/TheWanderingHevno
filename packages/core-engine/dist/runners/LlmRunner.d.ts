import { ProcessorNode } from '@hevno/schemas';
import { INodeRunner, ExecutionContext, CoreServices } from '../types';
export declare class LlmRunner implements INodeRunner {
    private clients;
    private getClient;
    run(node: ProcessorNode, inputs: Record<string, any>, context: ExecutionContext, services: CoreServices): Promise<Record<string, any>>;
}
