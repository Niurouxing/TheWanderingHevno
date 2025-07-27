// src/core/orchestrator.js

import { dispatch as dispatchLLM } from './llm_dispatcher.js';
import { APP, SYSTEM } from './manager.js';

/**
 * @class GenerationOrchestrator
 * @description 模块化生成流程的编排与执行引擎。
 */
export class GenerationOrchestrator {
    constructor(pipelineDefinition, initialSillyTavernContext) {
        this.pipeline = pipelineDefinition.filter(m => m.enabled);
        this.rawContext = initialSillyTavernContext;

        this.context = {
            sillyTavern: {
                character: this.rawContext.characters[this.rawContext.characterId],
                userInput: this.rawContext.chat.slice(-1)[0]?.mes || '',
                userName: this.rawContext.name1,
                chat: this.rawContext.chat,
            },
            outputs: {},
            module: {},
        };

        this.finalOutputModuleId = 'final_formatter';
    }

    _formatChatHistory(chatArray) {
        if (!Array.isArray(chatArray)) return '';
        return chatArray.map(message => {
            const prefix = message.is_user ? (this.context.sillyTavern.userName || 'User') : (this.context.sillyTavern.character?.name || 'Assistant');
            return `${prefix}: ${message.mes}`;
        }).join('\n');
    }

    _resolvePath(path, contextObject) {
        let current = contextObject;
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
        return current;
    }

    /**
     * This is the definitive solution. It works by creating a "bubble universe"
     * for the WI calculation by snapshotting and hijacking ALL relevant global states
     * that SillyTavern's `getSortedEntries` function and its children directly access.
     * This prevents any other WI source (character, chat, persona) from polluting
     * the calculation for our specific module.
     *
     * @param {object} module - The current module definition.
     * @param {string} preRenderedPrompt - The pre-rendered prompt for WI context.
     * @returns {Promise<string>} The activated World Info string for this module.
     */
    async _calculateModuleWorldInfo(module, preRenderedPrompt) {
        if (!module.worldInfo || !Array.isArray(module.worldInfo) || module.worldInfo.length === 0) {
            return '';
        }

        try {
            // 使用已导入的SYSTEM对象来获取世界书函数
            if (typeof SYSTEM.getWorldInfoPrompt !== 'function' || typeof SYSTEM.loadWorldInfo !== 'function') {
                console.error('[Orchestrator] World info functions not available in SYSTEM object');
                console.log('[Orchestrator] Available SYSTEM methods:', Object.keys(SYSTEM));
                return '';
            }

            // 备份原始状态
            const originalState = {
                selected_world_info: window.selected_world_info ? [...window.selected_world_info] : [],
                characters: window.characters ? [...window.characters] : [],
                chat_metadata: window.chat_metadata ? JSON.parse(JSON.stringify(window.chat_metadata)) : {},
                power_user_lorebook: window.power_user?.persona_description_lorebook
            };

            console.log(`[Orchestrator] Setting module WI: [${module.worldInfo.join(', ')}]`);

            // 初始化全局变量（如果不存在）
            if (!window.selected_world_info) {
                window.selected_world_info = [];
            }
            if (!window.characters) {
                window.characters = [];
            }
            if (!window.chat_metadata) {
                window.chat_metadata = {};
            }
            if (!window.power_user) {
                window.power_user = {};
            }

            // 设置模块的世界书为唯一选择
            window.selected_world_info.length = 0;
            window.selected_world_info.push(...module.worldInfo);

            // 清空其他世界书源
            window.characters.length = 0;
            Object.keys(window.chat_metadata).forEach(key => {
                delete window.chat_metadata[key];
            });

            window.power_user.persona_description_lorebook = undefined;

            // 预加载世界书缓存
            const loadPromises = module.worldInfo.map(worldName => SYSTEM.loadWorldInfo(worldName));
            await Promise.all(loadPromises);

            // 准备聊天上下文
            const chatMessages = this.rawContext.chat
                .filter(m => !m.is_system)
                .map(m => m.mes)
                .reverse();

            const maxContextSize = this.rawContext.max_context || 4096;

            // 准备全局扫描数据
            const globalScanData = {
                personaDescription: '',
                characterDescription: '',
                characterPersonality: '',
                characterDepthPrompt: '',
                scenario: '',
                creatorNotes: ''
            };

            console.log(`[Orchestrator] Calling getWorldInfoPrompt with ${chatMessages.length} messages, maxContext: ${maxContextSize}`);

            // 执行世界书计算
            const wiResult = await SYSTEM.getWorldInfoPrompt(chatMessages, maxContextSize, true, globalScanData);

            const moduleWiString = (wiResult?.worldInfoString || wiResult || '').toString().trim();
            console.log(`[Orchestrator] WI calculated. Length: ${moduleWiString.length}`);

            // 恢复原始状态
            window.selected_world_info.length = 0;
            window.selected_world_info.push(...originalState.selected_world_info);

            window.characters.length = 0;
            window.characters.push(...originalState.characters);

            Object.keys(window.chat_metadata).forEach(key => {
                delete window.chat_metadata[key];
            });
            Object.assign(window.chat_metadata, originalState.chat_metadata);

            if (originalState.power_user_lorebook !== undefined) {
                window.power_user.persona_description_lorebook = originalState.power_user_lorebook;
            }

            console.log('[Orchestrator] Original state restored.');
            return moduleWiString;

        } catch (error) {
            console.error(`[Orchestrator] Error calculating WI:`, error);
            console.error('[Orchestrator] Error stack:', error.stack);
            return '';
        }
    }


    _renderPrompt(module) {
        let fullPrompt = '';
        for (const slot of module.promptSlots) {
            if (slot.enabled) {
                const renderedContent = slot.content.replace(/{{(.*?)}}/g, (match, path) => {
                    const value = this._resolvePath(path.trim(), this.context);
                    if (value === undefined || value === null) return match;
                    if (path.trim() === 'sillyTavern.chat') return this._formatChatHistory(value);
                    if (typeof value === 'object') return JSON.stringify(value, null, 2);
                    return String(value);
                });
                fullPrompt += renderedContent + '\n';
            }
        }
        return fullPrompt.trim();
    }

    async _executeModule(module) {
        console.log(`[Hevno Orchestrator] Executing module: ${module.id} (${module.name})`);

        this.context.module = { worldInfo: '' };
        const promptForWiScan = this._renderPrompt(module);
        this.context.module.worldInfo = await this._calculateModuleWorldInfo(module, promptForWiScan);
        const finalPrompt = this._renderPrompt(module);
        console.log(`[Hevno Orchestrator] === START FINAL RENDERED PROMPT for ${module.id} ===\n${finalPrompt}\n=== END FINAL RENDERED PROMPT for ${module.id} ===`);

        try {
            const result = await dispatchLLM(finalPrompt, module.llm);
            this.context.outputs[module.id] = result;
            return { id: module.id, result };
        } catch (error) {
            console.error(`[Hevno Orchestrator] Failed to execute module ${module.id}:`, error);
            throw error;
        }
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
            if (!reverseDependencyGraph.has(module.id)) reverseDependencyGraph.set(module.id, new Set());
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

        const unexecutedModules = this.pipeline.filter(m => !(m.id in this.context.outputs));
        if (unexecutedModules.length > 0) {
            const unexecutedIds = unexecutedModules.map(m => m.id).join(', ');
            throw new Error(`Execution failed. A circular dependency may exist. Unexecuted modules: ${unexecutedIds}`);
        }

        console.log("[Hevno Orchestrator] Pipeline finished. All outputs:", this.context.outputs);
        const finalOutput = this.context.outputs[this.finalOutputModuleId];
        return finalOutput || "Pipeline completed, but no final output was designated.";
    }
}