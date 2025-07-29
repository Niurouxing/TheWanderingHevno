// packages/core-engine/src/runners/FunctionRunner.ts
import { 
    buildObjectValidatorFromSchema, 
    ProcessorNode,
    FunctionRuntime // 导入 FunctionRuntime
} from '@hevno/schemas';
import { INodeRunner, ExecutionContext, CoreServices } from '../types';

// 定义函数签名的类型别名，使其更清晰
type CoreFunction = (inputs: any, context: ExecutionContext, services: CoreServices) => Promise<any> | any;

export class FunctionRunner implements INodeRunner {
  // 将注册表作为类的私有属性
  private functionRegistry: Map<string, CoreFunction>;

  // 构造函数接收一个函数注册表
  constructor(registry: Map<string, CoreFunction>) {
    this.functionRegistry = registry;
    this.registerCoreFunctions();
  }

  // 注册核心函数
  private registerCoreFunctions() {
    this.functionRegistry.set('core:setVariable', async (inputs: { name: string; value: any }, context) => {
      context.variables[inputs.name] = inputs.value;
      console.log(`[core:setVariable] Set variable '${inputs.name}' to:`, inputs.value);
      return {}; // 通常不产生数据输出
    });

    this.functionRegistry.set('core:getVariable', async (inputs: { name: string }, context) => {
      const value = context.variables[inputs.name];
      return { value };
    });

    this.functionRegistry.set('core:runGraph', async (inputs: { graphId: string; [key: string]: any }, context, services) => {
      const { graphId, ...initialInputs } = inputs;
      const subgraph = services.graphRegistry.get(graphId);
      if (!subgraph) {
        throw new Error(`Subgraph with id "${graphId}" not found in registry.`);
      }

      // 准备子图的输入
      // 假设子图只有一个输入节点，并且其ID与子图ID相同（或约定好的名称）
      const subgraphInputNode = subgraph.nodes.find(n => n.type === 'input');
      if (!subgraphInputNode) {
        throw new Error(`Subgraph "${graphId}" has no input node.`);
      }
      const executionResult = await services.graphExecutor.execute(subgraph, {
        [subgraphInputNode.id]: initialInputs
      });
      
      // 返回子图的输出
      const subgraphOutputNode = subgraph.nodes.find(n => n.type === 'output');
      if (!subgraphOutputNode) return {};
      
      return executionResult.outputs[subgraphOutputNode.id];
    });
  }

  async run(
    node: ProcessorNode,
    inputs: Record<string, any>,
    context: ExecutionContext,
    services: CoreServices
  ): Promise<Record<string, any>> {
    if (node.runtime.type !== 'function') {
      throw new Error('Invalid node type for FunctionRunner');
    }

    const runtime = node.runtime as FunctionRuntime; // 类型断言
    const { functionName, inputSchema, outputSchema } = runtime;

    const func = this.functionRegistry.get(functionName);
    if (!func) {
      throw new Error(`Function "${functionName}" not found.`);
    }
    
    // 注意：这里的 inputs 已经是模板解析和上游节点连接的结果
    // 如果函数有静态配置，需要一种方式来合并。目前的设计里没有 config 字段，
    // 所有东西都应通过输入端口传入。
    const allInputs = { ...inputs };

    // --- 运行时输入验证 ---
    if (inputSchema) {
      try {
        const inputValidator = buildObjectValidatorFromSchema(inputSchema);
        inputValidator.parse(allInputs); 
        console.log(`[FunctionRunner] Input for ${functionName} validated successfully.`);
      } catch (error) {
        throw new Error(`Input validation failed for function "${functionName}" on node "${node.name}": ${error}`);
      }
    }

    // 执行核心函数
    const result = await Promise.resolve(func(allInputs, context, services));

    // --- 运行时输出验证 ---
    if (outputSchema) {
      try {
        const outputValidator = buildObjectValidatorFromSchema(outputSchema);
        outputValidator.parse(result);
        console.log(`[FunctionRunner] Output for ${functionName} validated successfully.`);
      } catch (error) {
        throw new Error(`Output validation failed for function "${functionName}" on node "${node.name}": ${error}`);
      }
    }

    return result;
  }
}