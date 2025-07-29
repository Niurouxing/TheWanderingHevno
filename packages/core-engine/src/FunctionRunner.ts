import { ProcessorNode } from '@hevno/schemas';
import { INodeRunner } from '../types';

// 函数注册表，未来插件可以向这里注册函数
const functionRegistry = new Map<string, (inputs: any) => any>();

// 示例函数
functionRegistry.set('add', (inputs) => ({ result: inputs.a + inputs.b }));
functionRegistry.set('concatenate', (inputs) => ({ result: `${inputs.str1}${inputs.str2}` }));

export class FunctionRunner implements INodeRunner {
  async run(node: ProcessorNode, inputs: Record<string, any>): Promise<Record<string, any>> {
    if (node.runtime.type !== 'function') {
      throw new Error('Invalid node type for FunctionRunner');
    }

    const func = functionRegistry.get(node.runtime.functionName);
    if (!func) {
      throw new Error(`Function "${node.runtime.functionName}" not found in registry.`);
    }

    // 执行函数并返回结果
    // 函数的返回值应该是一个对象，key 是输出端口的 ID
    const result = await Promise.resolve(func(inputs));
    return result;
  }
}