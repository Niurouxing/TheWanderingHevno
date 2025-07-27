// src/core/function_registry.js

import { USER } from './manager.js';

/**
 * @file function_registry.js
 * @description 存放所有可被FunctionNode调用的自定义JS函数。
 * 
 * 【设计哲学】
 * 1.  **上下文作为输入**: 每个函数都接收完整的编排器上下文(context)作为其唯一参数。
 *     这给予了函数读取任何已完成节点输出的能力。
 * 2.  **返回值为输出**: 函数的返回值将被直接存入 `context.outputs[currentNodeId]`。
 * 3.  **无副作用**: 函数应尽量保持纯净，主要负责数据转换和逻辑判断，避免直接操作DOM或进行异步API调用（除非特殊设计）。
 */
export const functionRegistry = {
    /**
     * @param {object} context - 完整的编排器上下文。
     * @returns {string[]} - 解析出的角色名称数组。
     */
    parseCharacterList: (context, params) => {
        const rawOutput = context.outputs[params.sourceNode];
        if (!rawOutput) return [];
        
        // [!code focus:start]
        // 【已修正】更健壮的解析逻辑
        const lowerCaseOutput = rawOutput.toLowerCase();
        
        // 检查是否明确指出没有角色
        if (lowerCaseOutput.includes('characters: none') || lowerCaseOutput.includes('characters:none')) {
            return [];
        }

        const matches = rawOutput.match(/Characters:(.*)/i); // i 表示不区分大小写
        if (matches && matches[1]) {
            const characterString = matches[1].trim();
            // 如果匹配到的部分是 "None" 或空，也返回空数组
            if (characterString.toLowerCase() === 'none' || characterString === '') {
                return [];
            }
            return characterString.split(',').map(name => name.trim()).filter(Boolean);
        }
        // [!code focus:end]
        return [];
    },

    /**
     * @param {object} context - 完整的编排器上下文。
     * @returns {boolean} - 是否继续流程。
     */
    isCombatRequired: (context, params) => {
        const rawOutput = context.outputs[params.sourceNode];
        if (!rawOutput) return false;
        // 简单判断，可以做的更复杂
        return rawOutput.toLowerCase().includes('yes');
    },

    /**
     * @param {object} context - 完整的编排器上下文。
     * @returns {string} - 清理后的文本。
     */
    stripLlmThinking: (context, params) => {
        const rawOutput = context.outputs[params.sourceNode];
        if (!rawOutput) return '';
        // 示例：移除 <thinking>...</thinking> 标签
        return rawOutput.replace(/<thinking>[\s\S]*?<\/thinking>/g, '').trim();
    },

    /**
     * @param {object} context - 完整的编排器上下文。
     * @returns {string} - 拼接后的故事文本。
     */
    aggregateStoryParts: (context, params) => {
        // [!code focus:start]
        // ======================= DEBUGGING START =======================
        console.log('[aggregateStoryParts] Received params:', JSON.stringify(params, null, 2));
        console.log('[aggregateStoryParts] All available node definitions:', Object.keys(context.nodes));
        // ======================= DEBUGGING END =======================
        // [!code focus:end]

        if (!params || !Array.isArray(params.sourceNodeIds) || params.sourceNodeIds.length === 0) {
            console.log('[aggregateStoryParts] No dynamic nodes to aggregate. Returning empty string.');
            return "";
        }

        const storyParts = params.sourceNodeIds.map(nodeId => {
            const characterAction = context.outputs[nodeId] || 'No action specified.'; // 确保有默认值
            
            // [!code focus:start]
            // ======================= DEBUGGING START =======================
            const dynamicNodeDef = context.nodes[nodeId];
            if (!dynamicNodeDef) {
                console.error(`[aggregateStoryParts] Could not find node definition for ID: ${nodeId}`);
                return `关于 Unknown Character (def not found):\n${characterAction}`;
            }
            console.log(`[aggregateStoryParts] Processing node ${nodeId}, injected params:`, JSON.stringify(dynamicNodeDef.injectedParams, null, 2));
            // ======================= DEBUGGING END =======================
            // [!code focus:end]

            const characterName = dynamicNodeDef.injectedParams?.item || 'Unknown Character';
            return `关于 ${characterName}:\n${characterAction}`;
        });
        
        return storyParts.join('\n\n');
    },

    /**
     * 检查输出是否符合要求。
     * @param {object} context 
     * @param {object} params - { sourceNode: string, attempts: number }
     * @returns {string} 'ok' or 'retry'
     */
    validateOutput: (context, params) => {
        const output = context.outputs[params.sourceNode];
        // 简单验证：输出不能为空
        if (output && output.trim().length > 10) {
            return 'ok';
        }
        // 还可以检查重试次数
        if (params.attempts >= 3) {
            console.warn(`[Validator] Node ${params.sourceNode} failed after 3 attempts.`);
            return 'fail';
        }
        return 'retry';
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