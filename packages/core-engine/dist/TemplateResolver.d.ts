import { ExecutionContext } from './types';
/**
 * 解析模板字符串，如 "Hello, {{input.name}}!"
 * @param template 模板字符串
 * @param context 当前的执行上下文
 * @returns 解析后的值，可以是字符串，也可以是对象/数组等原始值
 */
export declare function resolveTemplate(template: any, context: ExecutionContext): any;
