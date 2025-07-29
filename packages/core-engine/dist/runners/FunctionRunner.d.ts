import { ProcessorNode } from '@hevno/schemas';
import { INodeRunner, ExecutionContext, CoreServices } from '../types';
type CoreFunction = (inputs: any, context: ExecutionContext, services: CoreServices) => Promise<any> | any;
export declare class FunctionRunner implements INodeRunner {
    private functionRegistry;
    constructor(registry: Map<string, CoreFunction>);
    private registerCoreFunctions;
    run(node: ProcessorNode, inputs: Record<string, any>, context: ExecutionContext, services: CoreServices): Promise<Record<string, any>>;
}
export {};
