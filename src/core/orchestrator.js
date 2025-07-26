// src/core/orchestrator.js (V4 - 自动依赖检测版)

import { APP } from './manager.js';

/**
 * @class GenerationOrchestrator
 * @description 模块化生成流程的编排与执行引擎。
 *              能够通过解析prompt中的 {{outputs.*}} 占位符来自动推断模块间的依赖关系。
 */
export class GenerationOrchestrator {
    /**
     * @param {Array<object>} pipelineDefinition - 包含所有模块定义的数组。
     * @param {object} initialSillyTavernContext - 从 `APP.getContext()` 获取的原始上下文。
     */
    constructor(pipelineDefinition, initialSillyTavernContext) {
        this.pipeline = pipelineDefinition.filter(m => m.enabled);
        
        // 调试日志: 验证数据源头
        console.log('[DEBUG] Orchestrator received raw SillyTavern context:', initialSillyTavernContext);
        
        const context = initialSillyTavernContext;
        const mainCharacter = (context.characterId !== -1 && context.characters && context.characters[context.characterId]) 
                              ? context.characters[context.characterId] 
                              : null;

        this.initialContext = {
            sillyTavern: {
                chat: context.chat,
                character: mainCharacter, 
                userInput: context.chat.slice(-1)[0]?.mes || '',
                userName: context.name1,
            },
            outputs: {}, 
        };

        // 调试日志: 检查构建的上下文
        console.log('[DEBUG] Orchestrator constructed its own initialContext:', this.initialContext);
        if (this.initialContext.sillyTavern.character) {
            console.log(`[DEBUG]   - Constructed context has a character with name: ${this.initialContext.sillyTavern.character.name}`);
        } else {
            console.error('[DEBUG]   - CRITICAL: Constructed context does NOT have a character object!');
        }
        
        this.finalOutputModuleId = 'main_story_generator'; 
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
     * 根据路径从上下文中解析模板变量的值。
     * @param {string} path - 点分隔的路径，例如 'sillyTavern.character.name'。
     * @returns {*} 解析出的值，如果路径无效则返回undefined。
     */
    _resolvePath(path) {
        // 调试日志: 追踪路径解析
        console.log(`[DEBUG] _resolvePath: Trying to resolve path: "${path}"`);
        let current = this.initialContext;
        const parts = path.split('.');
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            if (current && typeof current === 'object' && part in current) {
                current = current[part];
            } else {
                console.error(`[DEBUG]   - FAILED! Key "${part}" not found in current object.`);
                return undefined;
            }
        }
        return current;
    }

    /**
     * 渲染一个模块的prompt模板。
     * @param {object} module - 模块定义。
     * @returns {string} 渲染后的完整prompt字符串。
     */
    _renderPrompt(module) {
        console.log(`[DEBUG] _renderPrompt: Rendering prompt for module "${module.id}"`);
        let fullPrompt = '';
        for (const slot of module.promptSlots) {
            if (slot.enabled) {
                const renderedContent = slot.content.replace(/{{(.*?)}}/g, (match, path) => {
                    const trimmedPath = path.trim();
                    const value = this._resolvePath(trimmedPath);

                    if (value === undefined || value === null) {
                        console.warn(`[DEBUG]   - Template variable "${trimmedPath}" resolved to undefined/null. Keeping original placeholder.`);
                        return match; 
                    }
                    if (trimmedPath === 'sillyTavern.chat' && Array.isArray(value)) {
                        return this._formatChatHistory(value);
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
        console.log(`[Hevno Orchestrator] Executing module: ${module.id}`);
        const finalPrompt = this._renderPrompt(module);
        
        console.log(`[Hevno Orchestrator] === START RENDERED PROMPT for ${module.id} ===\n${finalPrompt}\n=== END RENDERED PROMPT for ${module.id} ===`);

        // 模拟LLM调用
        const result = `(Mock Output for ${module.id})`; 
        await new Promise(resolve => setTimeout(resolve, Math.random() * 500 + 200)); 

        console.log(`[Hevno Orchestrator] Finished module: ${module.id}`);
        this.initialContext.outputs[module.id] = result;
        return { id: module.id, result };
    }

    /**
     * 【新增】从模块的prompt中解析出所有输出依赖。
     * @param {object} module - 模块定义。
     * @returns {Set<string>} 包含所有依赖模块ID的集合。
     */
    _extractDependencies(module) {
        const dependencies = new Set();
        const dependencyRegex = /{{\s*outputs\.(\w+)\s*}}/g; // 匹配 {{ outputs.模块ID }}

        for (const slot of (module.promptSlots || [])) {
            if (slot.enabled && slot.content) {
                const matches = slot.content.matchAll(dependencyRegex);
                for (const match of matches) {
                    dependencies.add(match[1]); // match[1] 是捕获组 (\w+)
                }
            }
        }
        return dependencies;
    }

    /**
     * 主执行函数，运行整个生成管线。
     * @returns {Promise<string>} 最终的生成结果。
     */
    async run() {
        console.log('[Hevno Orchestrator] Starting pipeline run with automatic dependency detection...');

        const dependencyGraph = new Map();
        const reverseDependencyGraph = new Map();
        const inDegree = new Map();

        // 动态构建依赖图
        for (const module of this.pipeline) {
            const dependencies = this._extractDependencies(module);
            console.log(`[DEBUG] Module "${module.id}" has auto-detected dependencies:`, Array.from(dependencies));
            
            dependencyGraph.set(module.id, dependencies);
            inDegree.set(module.id, dependencies.size);

            if (!reverseDependencyGraph.has(module.id)) {
                reverseDependencyGraph.set(module.id, new Set());
            }
            for (const dep of dependencies) {
                if (!reverseDependencyGraph.has(dep)) {
                    reverseDependencyGraph.set(dep, new Set());
                }
                reverseDependencyGraph.get(dep).add(module.id);
            }
        }

        // 拓扑排序执行
        let executionQueue = this.pipeline.filter(m => inDegree.get(m.id) === 0);

        while (executionQueue.length > 0) {
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

        // 检查循环依赖或失败的模块
        const unexecutedModules = this.pipeline.filter(m => !(m.id in this.initialContext.outputs));
        if (unexecutedModules.length > 0) {
            const unexecutedIds = unexecutedModules.map(m => m.id).join(', ');
            throw new Error(`Execution failed. A circular dependency may exist, or some modules failed. Unexecuted modules: ${unexecutedIds}`);
        }
        
        console.log("[Hevno Orchestrator] Pipeline finished. All outputs:", this.initialContext.outputs);

        // 渲染最终模块的输出
        const finalModule = this.pipeline.find(m => m.id === this.finalOutputModuleId);
        if (finalModule) {
            console.log(`[Hevno Orchestrator] Rendering final module for output: ${finalModule.id}`);
            const finalRenderedPrompt = this._renderPrompt(finalModule);
            // 最终输出也需要模拟，因为它可能依赖其他模块的真实输出
            const finalResult = `(Mock Final Output for ${finalModule.id})\n---\n${finalRenderedPrompt}`;
            console.log(`[Hevno Orchestrator] === START FINAL OUTPUT ===\n${finalResult}\n=== END FINAL OUTPUT ===`);
            return finalResult;
        }

        return "Pipeline completed, but no final output was designated.";
    }
}