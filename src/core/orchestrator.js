// src/core/orchestrator.js (V5 - 丰富上下文与增强格式化版)

import { APP } from './manager.js';

/**
 * @class GenerationOrchestrator
 * @description 模块化生成流程的编排与执行引擎。
 *              通过解析prompt中的 {{outputs.*}} 占位符自动推断模块依赖，并支持丰富的SillyTavern上下文变量。
 */
export class GenerationOrchestrator {
    /**
     * @param {Array<object>} pipelineDefinition - 包含所有模块定义的数组。
     * @param {object} initialSillyTavernContext - 从 `APP.getContext()` 获取的原始上下文。
     */
    constructor(pipelineDefinition, initialSillyTavernContext) {
        this.pipeline = pipelineDefinition.filter(m => m.enabled);
        
        const context = initialSillyTavernContext;
        const mainCharacter = (context.characterId !== -1 && context.characters && context.characters[context.characterId]) 
                              ? context.characters[context.characterId] 
                              : null;

        // 【增强点】构建一个更丰富的初始上下文，包含SillyTavern的常用数据
        this.initialContext = {
            sillyTavern: {
                chat: context.chat,
                character: mainCharacter,
                userInput: context.chat.slice(-1)[0]?.mes || '',
                userName: context.name1,
                // 新增：直接暴露更多有用信息
                worldInfo: context.worldInfo,
                authorsNote: context.authorsNote,
                charGreeting: mainCharacter?.first_mes || '',
            },
            // 用于存储各个模块的输出
            outputs: {}, 
        };

        console.log('[DEBUG] Orchestrator constructed its enriched initialContext:', this.initialContext);
        
        // 【可配置】指定哪个模块的输出是整个管线的最终结果
        this.finalOutputModuleId = 'final_formatter'; 
    }

    /**
     * 将聊天历史数组格式化为LLM可读的文本。
     * @param {Array<object>} chatArray - SillyTavern的聊天对象数组。
     * @returns {string} 格式化后的对话字符串。
     */
    _formatChatHistory(chatArray) {
        if (!Array.isArray(chatArray)) return '';
        return chatArray.map(message => {
            const prefix = message.is_user 
                ? (this.initialContext.sillyTavern.userName || 'User') 
                : (this.initialContext.sillyTavern.character?.name || 'Assistant');
            return `${prefix}: ${message.mes}`;
        }).join('\n');
    }

    /**
     * 【新增】格式化世界信息（World Info），使其更适合注入Prompt。
     * @param {Array<object>} worldInfoArray - SillyTavern的世界信息数组。
     * @returns {string} 格式化后的世界信息字符串。
     */
    _formatWorldInfo(worldInfoArray) {
        if (!Array.isArray(worldInfoArray)) return '';
        return worldInfoArray
            .filter(entry => entry.enabled) // 只使用启用的条目
            .map(entry => `[关键字: ${entry.key}]\n${entry.content}`)
            .join('\n\n---\n\n');
    }

    /**
     * 根据路径从上下文中解析模板变量的值。
     * @param {string} path - 点分隔的路径，例如 'sillyTavern.character.name'。
     * @returns {*} 解析出的值，如果路径无效则返回undefined。
     */
    _resolvePath(path) {
        let current = this.initialContext;
        const parts = path.split('.');
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            if (current && typeof current === 'object' && part in current) {
                current = current[part];
            } else {
                console.warn(`[Orchestrator] Path resolution failed. Key "${part}" not found in context for path "${path}".`);
                return undefined;
            }
        }
        console.log(`[DEBUG] _resolvePath: Resolved "${path}" successfully.`);
        return current;
    }

    /**
     * 渲染一个模块的prompt模板。
     * @param {object} module - 模块定义。
     * @returns {string} 渲染后的完整prompt字符串。
     */
    _renderPrompt(module) {
        let fullPrompt = '';
        for (const slot of module.promptSlots) {
            if (slot.enabled) {
                const renderedContent = slot.content.replace(/{{(.*?)}}/g, (match, path) => {
                    const trimmedPath = path.trim();
                    const value = this._resolvePath(trimmedPath);

                    if (value === undefined || value === null) {
                        console.warn(`[Orchestrator] Template variable "{{${trimmedPath}}}" resolved to undefined/null. Keeping original placeholder.`);
                        return match; 
                    }
                    
                    // 【增强点】使用专门的格式化函数处理特定数据类型
                    if (trimmedPath === 'sillyTavern.chat') {
                        return this._formatChatHistory(value);
                    }
                    if (trimmedPath === 'sillyTavern.worldInfo') {
                        return this._formatWorldInfo(value);
                    }
                    
                    if (typeof value === 'object' && !Array.isArray(value)) {
                        return JSON.stringify(value, null, 2);
                    }
                    return String(value);
                });
                fullPrompt += renderedContent + '\n';
            }
        }
        return fullPrompt.trim();
    }
    
    /**
     * 执行单个模块的逻辑。
     * @param {object} module - 要执行的模块定义。
     * @returns {Promise<{id: string, result: string}>} 包含模块ID和结果的对象。
     */
    async _executeModule(module) {
        console.log(`[Hevno Orchestrator] Executing module: ${module.id} (${module.name})`);
        const finalPrompt = this._renderPrompt(module);
        
        console.log(`[Hevno Orchestrator] === START RENDERED PROMPT for ${module.id} ===\n${finalPrompt}\n=== END RENDERED PROMPT for ${module.id} ===`);

        // ======================= 【核心修改点】 =======================
        // 创建一个“日志累加式”的模拟输出。
        // 这个输出会清晰地标明是哪个模块生成的，并完整地包含该模块接收到的最终输入(prompt)。
        // 这样，当模块之间相互引用时，输出会像滚雪球一样越来越大，
        // 最终结果将展示出整个数据流的完整路径。

        const result = `
<<<<<<<<<< START: MOCK OUTPUT for "${module.name}" [${module.id}] >>>>>>>>>>

[This module received the following prompt and produced this mock response based on it.]

--- [PROMPT FOR ${module.id}] ---
${finalPrompt}
--- [END PROMPT FOR ${module.id}] ---

<<<<<<<<<< END: MOCK OUTPUT for "${module.name}" [${module.id}] >>>>>>>>>>
`;
        // =============================================================

        await new Promise(resolve => setTimeout(resolve, Math.random() * 100 + 50)); // 缩短延迟以加快调试

        console.log(`[Hevno Orchestrator] Finished module: ${module.id}. Result stored.`);
        this.initialContext.outputs[module.id] = result;
        return { id: module.id, result };
    }

    _extractDependencies(module) {
        const dependencies = new Set();
        const dependencyRegex = /{{\s*outputs\.([\w_]+)\s*}}/g;
        for (const slot of (module.promptSlots || [])) {
            if (slot.enabled && slot.content) {
                const matches = slot.content.matchAll(dependencyRegex);
                for (const match of matches) {
                    dependencies.add(match[1]);
                }
            }
        }
        return dependencies;
    }

    async run() {
        console.log('[Hevno Orchestrator] Starting pipeline run with automatic dependency detection...');
        const dependencyGraph = new Map();
        const reverseDependencyGraph = new Map();
        const inDegree = new Map();

        for (const module of this.pipeline) {
            const dependencies = this._extractDependencies(module);
            dependencyGraph.set(module.id, dependencies);
            inDegree.set(module.id, dependencies.size);
            if (!reverseDependencyGraph.has(module.id)) {
                reverseDependencyGraph.set(module.id, new Set());
            }
            for (const dep of dependencies) {
                if (!reverseDependencyGraph.has(dep)) reverseDependencyGraph.set(dep, new Set());
                reverseDependencyGraph.get(dep).add(module.id);
            }
        }

        let executionQueue = this.pipeline.filter(m => inDegree.get(m.id) === 0);
        while (executionQueue.length > 0) {
            console.log(`[Hevno Orchestrator] Executing parallel batch of ${executionQueue.length} modules:`, executionQueue.map(m => m.id));
            const promises = executionQueue.map(module => this._executeModule(module));
            const results = await Promise.all(promises);
            const nextExecutionQueue = [];
            for (const { id } of results) {
                const dependents = reverseDependencyGraph.get(id) || [];
                for (const dependentId of dependents) {
                    const newDegree = inDegree.get(dependentId) - 1;
                    inDegree.set(dependentId, newDegree);
                    if (newDegree === 0) {
                        nextExecutionQueue.push(this.pipeline.find(m => m.id === dependentId));
                    }
                }
            }
            executionQueue = nextExecutionQueue;
        }

        const unexecutedModules = this.pipeline.filter(m => !(m.id in this.initialContext.outputs));
        if (unexecutedModules.length > 0) {
            const unexecutedIds = unexecutedModules.map(m => m.id).join(', ');
            throw new Error(`Execution failed. A circular dependency may exist. Unexecuted modules: ${unexecutedIds}`);
        }
        
        console.log("[Hevno Orchestrator] Pipeline finished. All outputs:", this.initialContext.outputs);

        // 【改进点】返回指定最终模块的真实（模拟）输出
        const finalOutput = this.initialContext.outputs[this.finalOutputModuleId];
        if (finalOutput) {
            console.log(`[Hevno Orchestrator] Returning final output from module: ${this.finalOutputModuleId}`);
            return finalOutput;
        }

        console.warn(`[Hevno Orchestrator] Pipeline completed, but the designated final output module "${this.finalOutputModuleId}" did not produce a result.`);
        return "Pipeline completed, but no final output was designated.";
    }
}