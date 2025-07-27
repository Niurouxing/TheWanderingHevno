// src/core/function_registry.js

import { USER } from './manager.js';

/**
 * @file function_registry.js
 * @description 存放所有可被FunctionNode调用的自定义JS函数。
 * 
 * 【设计哲学 V2 - 通用性与可组合性】
 * 1.  **单一职责**: 每个函数只做一件小事，并把它做好。例如，不将“检查文本”和“决定是否战斗”混为一谈。
 * 2.  **通用性**: 函数名应描述其通用行为，而不是某个特定的业务场景。例如，`textContains` 而不是 `isCombatRequired`。
 * 3.  **参数化**: 将硬编码的值（如 "yes", "<thinking>") 提取为参数，让用户在 Pipeline 定义中指定它们。
 * 4.  **上下文作为输入**: 每个函数都接收完整的编排器上下文(context)和节点参数(params)。
 * 5.  **可预测的输出**: 函数的返回值应该是简单、可预测的数据类型（字符串、数组、布尔值），以便于下游节点消费。
 */
export const functionRegistry = {
    // =================================================================
    // 文本处理工具 (Text Processing Utilities)
    // =================================================================

    /**
     * 【新】检查输入文本是否包含指定的关键字。
     * 这是 isCombatRequired 的通用替代品。
     * @param {object} context 
     * @param {object} params - { sourceNode: string, keyword: string, caseSensitive: boolean (default: false) }
     * @returns {boolean} 如果找到关键字，则返回 true，否则返回 false。
     */
    textContains: (context, params) => {
        const { sourceNode, keyword, caseSensitive = false } = params;
        if (!keyword) throw new Error("[textContains] 'keyword' parameter is required.");
        
        const rawOutput = context.outputs[sourceNode];
        if (typeof rawOutput !== 'string') return false;

        if (caseSensitive) {
            return rawOutput.includes(keyword);
        } else {
            return rawOutput.toLowerCase().includes(keyword.toLowerCase());
        }
    },

    /**
     * 【新】使用正则表达式替换文本内容。
     * 这是 stripLlmThinking 的通用替代品。
     * @param {object} context 
     * @param {object} params - { sourceNode: string, pattern: string, flags: string (default: 'g'), replacement: string (default: '') }
     * @returns {string} 处理后的字符串。
     */
    regexReplace: (context, params) => {
        const { sourceNode, pattern, flags = 'g', replacement = '' } = params;
        if (!pattern) throw new Error("[regexReplace] 'pattern' parameter is required.");

        const rawOutput = context.outputs[sourceNode];
        if (typeof rawOutput !== 'string') return '';

        try {
            const regex = new RegExp(pattern, flags);
            return rawOutput.replace(regex, replacement);
        } catch (e) {
            throw new Error(`[regexReplace] Invalid regex pattern: ${e.message}`);
        }
    },

    /**
     * 【新】使用正则表达式从文本中提取所有匹配项的特定捕获组。
     * 这是一个更底层的工具，可用于实现像 parseCharacterList 这样的功能。
     * @param {object} context 
     * @param {object} params - { sourceNode: string, pattern: string, flags: string (default: 'g'), groupIndex: number (default: 1) }
     * @returns {string[]} 包含所有匹配的捕获组文本的数组。
     */
    extractWithRegex: (context, params) => {
        const { sourceNode, pattern, flags = 'g', groupIndex = 1 } = params;
        if (!pattern) throw new Error("[extractWithRegex] 'pattern' parameter is required.");

        const rawOutput = context.outputs[sourceNode];
        if (typeof rawOutput !== 'string') return [];

        try {
            const regex = new RegExp(pattern, flags);
            const matches = [...rawOutput.matchAll(regex)];
            return matches.map(match => match[groupIndex] || '').filter(Boolean);
        } catch (e) {
            throw new Error(`[extractWithRegex] Invalid regex pattern: ${e.message}`);
        }
    },

    // =================================================================
    // 结构化数据处理 (Structured Data Processing)
    // =================================================================

    /**
     * 【保留并改进】这是一个高级便利函数，用于从特定格式的文本中解析角色列表。
     * 它内部使用了更通用的逻辑，但为常见任务提供了便利。
     * @param {object} context
     * @param {object} params - { sourceNode: string }
     * @returns {string[]} 解析出的角色名称数组。
     */
    parseCharacterList: (context, params) => {
        const rawOutput = context.outputs[params.sourceNode];
        if (!rawOutput) return [];
        
        const lowerCaseOutput = rawOutput.toLowerCase();
        
        // 检查是否明确指出没有角色
        if (lowerCaseOutput.includes('characters: none') || lowerCaseOutput.includes('characters:none')) {
            return [];
        }

        const matches = rawOutput.match(/Characters:(.*)/i);
        if (matches && matches[1]) {
            const characterString = matches[1].trim();
            if (characterString.toLowerCase() === 'none' || characterString === '') {
                return [];
            }
            return characterString.split(',').map(name => name.trim()).filter(Boolean);
        }
        return [];
    },

    /**
     * 【新】聚合来自 Map 节点的动态输出。
     * 这是 aggregateStoryParts 的通用、可配置的替代品。
     * @param {object} context
     * @param {object} params - { 
     *   sourceNodeIds: string[], 
     *   itemTemplate: string (e.g., "Action for {{item}}: {{output}}"), 
     *   separator: string (default: '\n\n') 
     * }
     * @returns {string} 拼接后的字符串。
     */
    joinFromDynamicNodes: (context, params) => {
        const { sourceNodeIds, itemTemplate, separator = '\n\n' } = params;
        if (!sourceNodeIds || !Array.isArray(sourceNodeIds)) return "";
        if (!itemTemplate) throw new Error("[joinFromDynamicNodes] 'itemTemplate' parameter is required.");
        
        const parts = sourceNodeIds.map(nodeId => {
            const output = context.outputs[nodeId] || '';
            const dynamicNodeDef = context.nodes[nodeId];
            const item = dynamicNodeDef?.injectedParams?.item || 'Unknown';
            
            return itemTemplate
                .replace(/{{output}}/g, output)
                .replace(/{{item}}/g, item);
        });
        
        return parts.join(separator);
    },

    // =================================================================
    // 验证与逻辑 (Validation & Logic)
    // =================================================================

    /**
     * 【新】验证输入文本的最小长度。
     * 可用于构建重试循环。
     * @param {object} context
     * @param {object} params - { sourceNode: string, minLength: number }
     * @returns {boolean} 如果文本长度大于等于 minLength，则返回 true。
     */
    validateMinLength: (context, params) => {
        const { sourceNode, minLength = 1 } = params;
        const rawOutput = context.outputs[sourceNode];
        if (typeof rawOutput !== 'string') return false;

        return rawOutput.trim().length >= minLength;
    }
};

/**
 * 安全地执行注册表中的函数。
 * @param {string} functionName - 要执行的函数名。
 * @param {object} context - 编排器上下文。
 * @param {object} params - 节点定义中的参数。
 * @returns {any} 函数的返回值。
 */
export function executeFunction(functionName, context, params) {
    if (typeof functionRegistry[functionName] !== 'function') {
        throw new Error(`Function "${functionName}" is not defined in the function registry.`);
    }
    return functionRegistry[functionName](context, params);
}