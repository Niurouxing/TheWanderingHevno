// src/core/orchestrator.js

import { dispatch as dispatchLLM } from './llm_dispatcher.js';
import { executeFunction } from './function_registry.js';
import { APP, SYSTEM } from './manager.js';

/**
 * @class GenerationOrchestrator
 * @description 模块化生成流程的编排与执行引擎（V2 - 支持动态图）。
 */
export class GenerationOrchestrator {
    // ... constructor 和其他辅助函数 (_formatChatHistory, _resolvePath, etc.) 保持不变 ...
    constructor(pipelineDefinition, initialSillyTavernContext) {
        this.initialPipeline = pipelineDefinition;
        this.rawContext = initialSillyTavernContext;

        // 运行时的状态
        this.nodes = {}; // 存储所有节点定义，包括动态生成的
        this.nodeStates = {}; // 'pending', 'running', 'completed', 'failed', 'skipped'
        this.dependencies = new Map(); // node_id -> Set<dependency_id>
        this.dependents = new Map(); // node_id -> Set<dependent_id>

        // 【新增】世界书访问互斥锁
        this.worldInfoMutex = Promise.resolve();

        this.context = {
            sillyTavern: {
                character: this.rawContext.characters[this.rawContext.characterId],
                userInput: this.rawContext.chat.slice(-1)[0]?.mes || '',
                userName: this.rawContext.name1,
                chat: this.rawContext.chat,
            },
            outputs: {}, // 所有节点的输出都存在这里
            nodes: this.nodes, // 让FunctionNode可以访问节点定义
            module: {}, // 旧的模块上下文，保持兼容性
        };

        this.finalOutputNodeId = 'final_formatter'; // 可以从管线元数据中读取
    }

    _formatChatHistory(chatArray) {
        if (!Array.isArray(chatArray)) return '';
        return chatArray.map(message => {
            const prefix = message.is_user ? (this.context.sillyTavern.userName || 'User') : (this.context.sillyTavern.character?.name || 'Assistant');
            return `${prefix}: ${message.mes}`;
        }).join('\n');
    }

    _resolvePath(path, contextObject) {
        // 允许注入动态参数，例如来自MapNode
        if (path.startsWith('item')) {
            const dynamicValue = path.split('.').reduce((acc, part) => (acc ? acc[part] : undefined), contextObject);
            if (dynamicValue !== undefined) return dynamicValue;
        }

        let current = contextObject;
        const parts = path.split('.');
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            if (current && typeof current === 'object' && part in current) {
                current = current[part];
            } else {
                // [!code focus:start]
                // 【已修正】只在路径不是一个可选的 'outputs' 时才发出警告。
                // 这是为了避免在处理由路由器跳过的节点的输出时产生不必要的控制台噪音。
                if (!path.startsWith('outputs.')) {
                    console.warn(`[Orchestrator] Path resolution failed. Key "${part}" not found in context for path "${path}".`);
                }
                // [!code focus:end]
                return undefined;
            }
        }
        return current;
    }



    async _calculateModuleWorldInfo(module, preRenderedPrompt) {
        // 【注意】这个函数现在在 _executeLLMNode 的互斥锁保护下运行，不需要再次加锁
        
        // 1. 如果模块没有配置World Info，则提前返回。
        if (!module.worldInfo || !Array.isArray(module.worldInfo) || module.worldInfo.length === 0) {
            return '';
        }

        // 2. 检查必要的SillyTavern函数是否存在。
        if (typeof SYSTEM.getWorldInfoPrompt !== 'function' || typeof SYSTEM.loadWorldInfo !== 'function') {
            console.error('[Orchestrator] World Info functions are not available in the SYSTEM manager.');
            return '';
        }

            // 3. 备份需要临时修改的全局状态。
            // 首先获取当前的世界书状态
            const currentSelectedWorldInfo = SYSTEM.getSelectedWorldInfo();
            const currentCharacters = SYSTEM.getCharacters();
            const currentCharacterId = SYSTEM.getCurrentCharacterId();
            const currentChatMetadata = SYSTEM.getChatMetadata();
            const currentPowerUser = SYSTEM.getPowerUser();
            
            const originalState = {
                selected_world_info: currentSelectedWorldInfo,
                // 仅备份角色绑定的世界书，而不是整个角色对象
                character_worlds: currentCharacters ? currentCharacters.map(c => c.data?.extensions?.world) : [],
                chat_lorebook: currentChatMetadata ? currentChatMetadata[SYSTEM.METADATA_KEY] : undefined,
                persona_lorebook: currentPowerUser?.persona_description_lorebook,
            };

            try {
                console.log(`[Orchestrator] Calculating WI for module with books: [${module.worldInfo.join(', ')}]`);

                // 4. 改进的模块类型判断逻辑
                // 优先检查原始节点定义中的世界书配置来确定模块意图
                let isCharacterScoped = false;
                
                // 对于动态生成的节点，需要检查其模板节点的世界书配置
                if (module.id.includes('character_action_template')) {
                    // 这是一个动态生成的角色分析节点
                    isCharacterScoped = true;
                } else {
                    // 对于其他节点，检查其世界书配置来推断意图
                    // 如果世界书名包含 'character' 或类似关键词，则认为是角色相关
                    const hasCharacterWorldInfo = module.worldInfo.some(wi => 
                        wi.toLowerCase().includes('character') || wi.toLowerCase().includes('char')
                    );
                    isCharacterScoped = hasCharacterWorldInfo;
                }

                console.log(`[Orchestrator] Module ${module.id} determined as ${isCharacterScoped ? 'character-scoped' : 'global-scoped'}`);

                // 5. 【强化清理】完全重置世界书状态，清除所有累积的内容
                // 清除所有已选择的世界书
                SYSTEM.setSelectedWorldInfo([]);
                
                // 【新增】强制清理SillyTavern内部的世界书缓存和状态
                if (typeof SYSTEM.clearWorldInfoCache === 'function') {
                    SYSTEM.clearWorldInfoCache();
                }
                
                // 清除所有其他世界书来源
                if (currentPowerUser && 'persona_description_lorebook' in currentPowerUser) {
                    currentPowerUser.persona_description_lorebook = undefined;
                }
                
                if (currentChatMetadata && SYSTEM.METADATA_KEY in currentChatMetadata) {
                    SYSTEM.setChatMetadata(SYSTEM.METADATA_KEY, undefined);
                }
                
                if (currentCharacters) {
                    currentCharacters.forEach(c => {
                        if (c.data?.extensions) c.data.extensions.world = undefined;
                    });
                }
                
                // 【关键修复】强制等待，确保所有清理操作生效
                await new Promise(resolve => setTimeout(resolve, 10));

                // 6. 【修复策略改变】统一使用全局世界书机制，确保一致性
                if (isCharacterScoped) {
                    // 角色相关模块：使用全局世界书机制，但只设置角色相关的世界书
                    SYSTEM.setSelectedWorldInfo(module.worldInfo);
                    console.log(`[Orchestrator] Setting character-related global lore to: [${module.worldInfo.join(', ')}]`);
                    
                    // 不设置角色绑定的世界书，避免冲突
                } else {
                    // 全局相关模块：使用全局世界书机制
                    SYSTEM.setSelectedWorldInfo(module.worldInfo);
                    console.log(`[Orchestrator] Setting global lore to: [${module.worldInfo.join(', ')}]`);
                }

                // 7. 【强化修复】彻底重新加载世界书，确保正确设置
                console.log(`[Orchestrator] Loading world info files: [${module.worldInfo.join(', ')}]`);
                
                // 【关键】先强制卸载所有已加载的世界书数据（但保留选择列表）
                if (typeof SYSTEM.unloadAllWorldInfo === 'function') {
                    await SYSTEM.unloadAllWorldInfo();
                    console.log(`[Orchestrator] Cleared previous world info data`);
                }
                
                // 然后只加载当前模块需要的世界书
                for (const worldName of module.worldInfo) {
                    try {
                        await SYSTEM.loadWorldInfo(worldName);
                        console.log(`[Orchestrator] Successfully loaded world info: ${worldName}`);
                    } catch (error) {
                        console.warn(`[Orchestrator] Failed to load world info "${worldName}":`, error);
                    }
                }
                
                // 【关键修复】确保选择列表正确设置（重新设置，确保生效）
                SYSTEM.setSelectedWorldInfo(module.worldInfo);
                
                // 强制等待，确保设置生效
                await new Promise(resolve => setTimeout(resolve, 50));
                
                // 7.5. 【调试】验证世界书设置情况
                const finalSelectedWI = SYSTEM.getSelectedWorldInfo();
                console.log(`[Orchestrator] After setup - Selected WI: [${finalSelectedWI.join(', ')}]`);
                
                // 【安全检查】如果选择列表仍然为空，说明有问题
                if (finalSelectedWI.length === 0) {
                    console.error(`[Orchestrator] CRITICAL: Selected WI is empty after setup for module ${module.id}`);
                    // 尝试强制重新设置
                    SYSTEM.setSelectedWorldInfo([...module.worldInfo]);
                    console.log(`[Orchestrator] Force re-set Selected WI: [${SYSTEM.getSelectedWorldInfo().join(', ')}]`);
                }
                
                console.log(`[Orchestrator] World info setup complete for module: ${module.id}`);

                // 【新增】强制等待一个事件循环，确保所有状态更改生效
                await new Promise(resolve => setTimeout(resolve, 10));

                // 8. 准备参数并调用SillyTavern的核心WI计算函数。
                // 【修复】使用更符合SillyTavern内部格式的消息结构
                const chatMessages = this.rawContext.chat
                    .filter(m => !m.is_system)
                    .map(m => m.mes);
                
                // 【重要】不要reverse，保持原始顺序，SillyTavern会在内部处理
                const maxContextSize = this.rawContext.max_context || 4096;
                
                // 【修复】使用更完整的扫描数据，包括当前用户输入
                const globalScanData = {
                    personaDescription: this.rawContext.persona?.description ?? '',
                    characterDescription: this.context.sillyTavern.character?.description ?? '',
                    characterPersonality: this.context.sillyTavern.character?.personality ?? '',
                    characterDepthPrompt: this.context.sillyTavern.character?.data?.extensions?.depth_prompt ?? '',
                    scenario: this.rawContext.scenario ?? '',
                    creatorNotes: this.context.sillyTavern.character?.creatornotes ?? '',
                    // 【新增】包含当前的用户输入，这可能是激活世界书的关键
                    userInput: this.context.sillyTavern.userInput ?? '',
                };

                console.log(`[Orchestrator] Calling getWorldInfoPrompt for module...`);
                console.log(`[Orchestrator] Chat messages count: ${chatMessages.length}, Max context: ${maxContextSize}`);
                console.log(`[Orchestrator] Global scan data:`, globalScanData);
                
                // 【修复】尝试不同的调用模式，可能需要传递当前用户输入作为扫描内容
                const scanContent = [
                    globalScanData.userInput,
                    globalScanData.characterDescription,
                    globalScanData.scenario,
                    ...chatMessages.slice(-3) // 最近3条消息
                ].filter(Boolean).join('\n');
                
                console.log(`[Orchestrator] Scan content for WI activation:`, scanContent.substring(0, 200));
                
                const wiResult = await SYSTEM.getWorldInfoPrompt(chatMessages, maxContextSize, true, globalScanData);
                
                console.log(`[Orchestrator] Raw WI result:`, wiResult);

                let moduleWiString = (wiResult?.worldInfoString || '').trim();
                
                console.log(`[Orchestrator] Module WI calculated. Length: ${moduleWiString.length}`);
                if (moduleWiString.length > 0) {
                    console.log(`[Orchestrator] Module WI content preview: ${moduleWiString.substring(0, 200)}${moduleWiString.length > 200 ? '...' : ''}`);
                } else {
                    console.warn(`[Orchestrator] No world info was generated for module ${module.id} with books [${module.worldInfo.join(', ')}]`);
                    
                    // 【调试信息】检查当前的世界书状态
                    console.log(`[Orchestrator] Debug - Current selected_world_info:`, SYSTEM.getSelectedWorldInfo());
                }

                // 创建延迟恢复函数
                const restoreFunction = async () => {
                    console.log('[Orchestrator] Restoring original SillyTavern state...');

                    // 【延迟恢复】为了避免影响同时进行的其他世界书计算，稍作延迟
                    await new Promise(resolve => setTimeout(resolve, 50));

                    SYSTEM.setSelectedWorldInfo(originalState.selected_world_info);

                    if (originalState.persona_lorebook !== undefined && currentPowerUser) {
                        currentPowerUser.persona_description_lorebook = originalState.persona_lorebook;
                    }
                    
                    if (originalState.chat_lorebook !== undefined) {
                        SYSTEM.setChatMetadata(SYSTEM.METADATA_KEY, originalState.chat_lorebook);
                    }
                    
                    if (currentCharacters && originalState.character_worlds.length > 0) {
                        currentCharacters.forEach((c, i) => {
                            if (c.data?.extensions && i < originalState.character_worlds.length) {
                                c.data.extensions.world = originalState.character_worlds[i];
                            }
                        });
                    }

                    console.log('[Orchestrator] Original state restored successfully.');
                };

                return { worldInfo: moduleWiString, restoreFunction };

            } catch (error) {
                console.error(`[Orchestrator] An error occurred during module WI calculation:`, error);
                return { worldInfo: '', restoreFunction: null };
            }
    }

    _renderPrompt(node, injectedParams = {}) {
        let fullPrompt = '';
        const renderContext = { ...this.context, ...injectedParams };
        for (const slot of node.promptSlots) {
            if (slot.enabled) {
                const renderedContent = slot.content.replace(/{{(.*?)}}/g, (match, path) => {
                    const value = this._resolvePath(path.trim(), renderContext);
                    // [!code focus:start]
                    // 【已修正】如果路径解析结果为 undefined 或 null，则将其视为空字符串。
                    // 这对于处理可选的、被跳过的分支节点的输出至关重要。
                    if (value === undefined || value === null) {
                        return ''; // 返回空字符串，而不是保留占位符
                    }
                    // [!code focus:end]
                    if (path.trim() === 'sillyTavern.chat') return this._formatChatHistory(value);
                    if (typeof value === 'object') return JSON.stringify(value, null, 2);
                    return String(value);
                });
                fullPrompt += renderedContent + '\n';
            }
        }
        return fullPrompt.trim();
    }

    // [!code focus:99]
    // =================================================================
    // NEW DYNAMIC EXECUTION LOGIC
    // =================================================================

    // [!code focus:start]
    /**
     * 【已修正】构建完整的依赖图。
     * 此版本会检查所有可能定义依赖关系的地方。
     */
    _initializeGraph() {
        // 清理旧状态
        Object.keys(this.nodes).forEach(key => delete this.nodes[key]);
        this.nodeStates = {};
        this.dependencies.clear();
        this.dependents.clear();

        // 步骤 1: 加载所有节点的基本信息
        for (const nodeDef of this.initialPipeline) {
            if (nodeDef.enabled) {
                this.nodes[nodeDef.id] = JSON.parse(JSON.stringify(nodeDef));
                this.nodeStates[nodeDef.id] = 'pending';
                this.dependencies.set(nodeDef.id, new Set());
                this.dependents.set(nodeDef.id, new Set());
            }
        }

        // 步骤 2: 遍历所有节点，为它们添加依赖
        const dependencyRegex = /{{\s*outputs\.([\w.-]+)\s*}}/g;

        for (const nodeId in this.nodes) {
            const node = this.nodes[nodeId];
            const nodeDependencies = this.dependencies.get(nodeId);

            // a. 从模板/prompt中提取 '{{outputs...}}' 依赖
            const contentToCheck = JSON.stringify(node.promptSlots || '');
            for (const match of contentToCheck.matchAll(dependencyRegex)) {
                if (this.nodes[match[1]]) {
                    nodeDependencies.add(match[1]);
                }
            }

            // b. 【新增】检查特定节点类型的参数依赖
            const params = node.params || {};
            if (params.sourceNode && this.nodes[params.sourceNode]) {
                nodeDependencies.add(params.sourceNode);
            }
            if (params.sourceNodeIds && Array.isArray(params.sourceNodeIds)) {
                params.sourceNodeIds.forEach(id => {
                    if (this.nodes[id]) nodeDependencies.add(id);
                });
            }

            // c. 【新增】检查MapNode和Router的特定依赖
            if (node.type === 'map' && node.inputListRef) {
                const listSourceMatch = node.inputListRef.match(/outputs\.([\w.-]+)/);
                if (listSourceMatch && this.nodes[listSourceMatch[1]]) {
                    nodeDependencies.add(listSourceMatch[1]);
                }
            }
            if (node.type === 'router' && node.condition) {
                const conditionMatch = node.condition.match(/outputs\.([\w.-]+)/);
                if (conditionMatch && this.nodes[conditionMatch[1]]) {
                    nodeDependencies.add(conditionMatch[1]);
                }
            }
        }

        // 步骤 3: 专门处理结构性依赖（在所有其他依赖建立之后）
        for (const nodeId in this.nodes) {
            const node = this.nodes[nodeId];

            // a. JoinNode 依赖于 MapNode
            if (node.type === 'map' && node.joinNode) {
                const joinNodeId = node.joinNode;
                if (this.dependencies.has(joinNodeId)) {
                    this.dependencies.get(joinNodeId).add(nodeId);
                }
            }

            // b. 路由器的分支目标依赖于路由器本身
            if (node.type === 'router' && node.routes) {
                for (const routeKey in node.routes) {
                    const targetNodeId = node.routes[routeKey];
                    if (this.dependencies.has(targetNodeId)) {
                        this.dependencies.get(targetNodeId).add(nodeId);
                    }
                }
            }
        }
        // [!code focus:end]

        // 步骤 4: 构建反向依赖图 (dependents)
        for (const [nodeId, deps] of this.dependencies.entries()) {
            for (const depId of deps) {
                if (this.dependents.has(depId)) {
                    this.dependents.get(depId).add(nodeId);
                }
            }
        }

        console.log('[GraphInit] Dependency graph constructed:', this.dependencies);
    }

    async _executeNode(nodeId) {
        const node = this.nodes[nodeId];
        if (!node) {
            throw new Error(`Node with ID "${nodeId}" not found.`);
        }

        console.log(`[Orchestrator] > Executing ${node.type.toUpperCase()} node: ${node.id} (${node.name})`);

        switch (node.type) {
            case 'llm':
                this.context.outputs[node.id] = await this._executeLLMNode(node);
                break;
            case 'function':
                this.context.outputs[node.id] = await this._executeFunctionNode(node);
                break;
            case 'router':
                // Router的执行只做决策，不改变图的状态
                await this._executeRouterNode(node);
                break;
            case 'map':
                await this._executeMapNode(node);
                break;
            default:
                throw new Error(`Unsupported node type: "${node.type}"`);
        }
    }

    async _executeLLMNode(node) {
        // 【优化策略】分离世界书计算和LLM调用，只对世界书计算进行串行化
        
        // 第一阶段：串行化的世界书计算
        let worldInfoContent = '';
        let restoreFunction = null; // 用于延迟恢复状态
        
        if (node.worldInfo && Array.isArray(node.worldInfo) && node.worldInfo.length > 0) {
            // 等待之前的世界书操作完成
            await this.worldInfoMutex;
            
            // 创建新的互斥锁Promise来保护当前的世界书计算
            /** @type {function} */
            let resolveCurrentMutex = null;
            this.worldInfoMutex = new Promise(resolve => {
                resolveCurrentMutex = resolve;
            });
            
            try {
                const promptForWiScan = this._renderPrompt(node, node.injectedParams);
                const result = await this._calculateModuleWorldInfo(node, promptForWiScan);
                
                // 处理新的返回格式
                if (result && typeof result === 'object' && 'worldInfo' in result) {
                    worldInfoContent = result.worldInfo || '';
                    restoreFunction = result.restoreFunction; // 获取恢复函数
                } else {
                    // 向后兼容，如果返回的是字符串
                    worldInfoContent = String(result || '');
                }
                
                console.log(`[Orchestrator] World info calculated for ${node.id}, length: ${worldInfoContent.length}`);
            } finally {
                // 释放世界书计算的互斥锁
                if (resolveCurrentMutex) {
                    resolveCurrentMutex();
                }
            }
        }
        
        // 第二阶段：并发的LLM调用（不需要互斥锁保护）
        this.context.module = { worldInfo: worldInfoContent };
        const finalPrompt = this._renderPrompt(node, node.injectedParams);
        console.log(`[Orchestrator] === START LLM PROMPT for ${node.id} ===\n${finalPrompt}\n=== END LLM PROMPT for ${node.id} ===`);

        const result = await dispatchLLM(finalPrompt, node.llm);

        console.log(`[Orchestrator] === START LLM OUTPUT for ${node.id} ===\n${result}\n=== END LLM OUTPUT for ${node.id} ===`);

        // 【延迟恢复】在LLM调用完成后恢复状态
        if (restoreFunction) {
            await restoreFunction();
        }

        // 【新增】如果输出为空，给一个默认值防止后续模板渲染出错
        return result || '';
    }


    async _executeFunctionNode(node) {
        return executeFunction(node.functionName, this.context, node.params);
    }

    async _executeRouterNode(node) {
        const conditionValueRaw = this._resolvePath(node.condition.replace(/{{|}}/g, '').trim(), this.context);
        const conditionValue = String(conditionValueRaw).trim().toLowerCase();

        let chosenNextNodeId = null;
        for (const routeKey in node.routes) {
            // 支持用 'default' 作为备用路由
            if (routeKey.toLowerCase() === conditionValue) {
                chosenNextNodeId = node.routes[routeKey];
                break;
            }
        }

        // 如果没有精确匹配，检查是否有 'default' 路由
        if (!chosenNextNodeId && node.routes.default) {
            chosenNextNodeId = node.routes.default;
        }

        console.log(`[Router:${node.id}] Condition value is "${conditionValue}". Routing to -> ${chosenNextNodeId || 'end of branch'}.`);

        // 将决策结果存起来，以便 run 函数使用
        this.context.outputs[node.id] = { decision: chosenNextNodeId };
    }


    async _executeMapNode(node) {
        const list = this._resolvePath(node.inputListRef.replace(/{{|}}/g, '').trim(), this.context);
        const joinNodeId = node.joinNode;

        if (!Array.isArray(list) || list.length === 0) {
            console.warn(`[MapNode:${node.id}] Input list is empty or not an array. Informing join node.`);
            if (joinNodeId && this.nodes[joinNodeId]) {
                if (!this.nodes[joinNodeId].params) {
                    this.nodes[joinNodeId].params = {};
                }
                this.nodes[joinNodeId].params.sourceNodeIds = [];
            }
            return;
        }

        const templateNode = node.templateNode;
        const dynamicNodeIds = [];

        for (let i = 0; i < list.length; i++) {
            const item = list[i];
            const newNodeId = `${templateNode.id}_${i}`;

            const newNode = JSON.parse(JSON.stringify(templateNode));
            newNode.id = newNodeId;
            newNode.name = `${templateNode.name} for "${item}"`;
            newNode.injectedParams = { item: item };
            newNode.enabled = true;

            this.nodes[newNodeId] = newNode;
            this.nodeStates[newNodeId] = 'pending';
            dynamicNodeIds.push(newNodeId);

            // 动态节点的依赖是 Map 节点本身
            this.dependencies.set(newNodeId, new Set([node.id]));
            if (!this.dependents.has(node.id)) this.dependents.set(node.id, new Set());
            this.dependents.get(node.id).add(newNodeId);

            console.log(`[MapNode:${node.id}] Spawned dynamic node: ${newNodeId}`);
        }

        if (joinNodeId && this.nodes[joinNodeId]) {
            const joinNode = this.nodes[joinNodeId];
            const joinNodeDeps = this.dependencies.get(joinNodeId) || new Set();

            // JoinNode 依赖于所有动态生成的节点
            dynamicNodeIds.forEach(id => {
                joinNodeDeps.add(id);
                // 同时，建立反向依赖
                if (!this.dependents.has(id)) this.dependents.set(id, new Set());
                this.dependents.get(id).add(joinNodeId);
            });

            this.dependencies.set(joinNodeId, joinNodeDeps);

            if (!joinNode.params) joinNode.params = {};
            joinNode.params.sourceNodeIds = dynamicNodeIds; // 注入动态ID列表
        }
    }

    async run() {
        console.log('[Orchestrator V2] Starting dynamic graph execution...');
        this._initializeGraph();

        const inDegree = new Map();
        for (const nodeId in this.nodes) {
            inDegree.set(nodeId, this.dependencies.get(nodeId)?.size || 0);
        }

        let executionQueue = Object.keys(this.nodes).filter(nodeId => inDegree.get(nodeId) === 0);
        let completedOrSkippedCount = 0;

        while (executionQueue.length > 0) {
            console.log(`[Orchestrator] Executing parallel batch of ${executionQueue.length} nodes:`, executionQueue.map(id => this.nodes[id]?.name || id));

            const currentBatch = [...executionQueue];
            executionQueue = [];

            const promises = currentBatch.map(async (nodeId) => {
                try {
                    // 防御性检查，防止跳过的节点被错误执行
                    if (this.nodeStates[nodeId] !== 'pending') return;

                    this.nodeStates[nodeId] = 'running';
                    await this._executeNode(nodeId);
                    this.nodeStates[nodeId] = 'completed';
                } catch (error) {
                    this.nodeStates[nodeId] = 'failed';
                    const nodeName = this.nodes[nodeId]?.name || 'Unknown Node';
                    console.error(`Execution failed at node ${nodeName} (${nodeId}):`, error);
                    // 抛出错误以停止整个流程
                    throw new Error(`Execution failed at node ${nodeName}: ${error.message}`);
                }
            });

            await Promise.all(promises);

            // [!code focus:start]
            // ========================= 核心修正逻辑 START =========================
            // 在处理下游节点之前，检查刚刚完成的批次中是否有MapNode。
            // 如果有，图的结构已经改变，我们必须更新inDegree映射。
            for (const completedNodeId of currentBatch) {
                const node = this.nodes[completedNodeId];
                if (node.type === 'map') {
                    const joinNodeId = node.joinNode;
                    const dynamicNodeIds = this.nodes[joinNodeId]?.params?.sourceNodeIds || [];

                    // 1. 为所有新生成的动态节点设置初始inDegree
                    for (const dynamicNodeId of dynamicNodeIds) {
                        // 新节点在创建时已设置依赖，这里直接从 this.dependencies 获取
                        const initialDegree = this.dependencies.get(dynamicNodeId)?.size || 0;
                        inDegree.set(dynamicNodeId, initialDegree);

                        // 【补充检查】如果新节点的入度为0，它应该被加入下一个执行队列
                        // 但在你的设计中，动态节点的依赖是MapNode本身，所以它的入度至少为1，
                        // 并且会在MapNode完成后递减，所以这里的逻辑是安全的。
                    }

                    // 2. 更新JoinNode的inDegree，因为它获得了新的依赖
                    if (joinNodeId && this.nodes[joinNodeId]) {
                        // 【重要修正】这里的逻辑需要调整。不应该是 oldDegree + newDegree。
                        // 应该是直接从 this.dependencies 重新计算。
                        // 但考虑到拓扑排序的递减性质，更好的方法是增加它的 inDegree。
                        const currentDegree = inDegree.get(joinNodeId) || 0;
                        inDegree.set(joinNodeId, currentDegree + dynamicNodeIds.length);
                        console.log(`[GraphUpdate] JoinNode ${joinNodeId} inDegree increased by ${dynamicNodeIds.length}, new total: ${inDegree.get(joinNodeId)}`);
                    }
                }
            }
            // ========================= 核心修正逻辑 END =========================
            // [!code focus:end]


            let nodesToProcessForDependents = new Set(currentBatch);

            // 处理刚刚完成的节点，特别是Router
            for (const completedNodeId of currentBatch) {
                const node = this.nodes[completedNodeId];
                if (node.type === 'router') {
                    const decision = this.context.outputs[completedNodeId]?.decision;
                    for (const routeKey in node.routes) {
                        const targetNodeId = node.routes[routeKey];
                        if (targetNodeId !== decision && this.nodes[targetNodeId] && this.nodeStates[targetNodeId] === 'pending') {
                            this.nodeStates[targetNodeId] = 'skipped';
                            nodesToProcessForDependents.add(targetNodeId);
                            console.log(`[Router:${node.id}] Skipped node ${targetNodeId}`);
                        }
                    }
                }
            }

            completedOrSkippedCount += nodesToProcessForDependents.size;

            // 为所有新完成或跳过的节点，更新其下游节点的入度
            for (const processedNodeId of nodesToProcessForDependents) {
                const dependents = this.dependents.get(processedNodeId) || new Set();

                for (const dependentId of dependents) {
                    if (this.nodeStates[dependentId] === 'pending') {
                        const newDegree = (inDegree.get(dependentId) || 1) - 1;
                        inDegree.set(dependentId, newDegree);

                        if (newDegree === 0) {
                            executionQueue.push(dependentId);
                        }
                    }
                }
            }
        }

        const totalNodes = Object.keys(this.nodes).length;
        if (completedOrSkippedCount < totalNodes) {
            const unexecutedNodes = Object.keys(this.nodes).filter(id => this.nodeStates[id] === 'pending');
            const unexecutedNames = unexecutedNodes.map(id => this.nodes[id]?.name || id).join(', ');
            console.error(`[Orchestrator] Execution incomplete. ${unexecutedNodes.length} nodes were not executed, possibly due to a dependency cycle or graph error. Unexecuted:`, unexecutedNames);
            throw new Error(`Execution failed. Unexecuted nodes: ${unexecutedNames}`);
        }

        console.log("[Orchestrator] Pipeline finished. All outputs:", this.context.outputs);
        const finalOutput = this.context.outputs[this.finalOutputNodeId];
        return finalOutput || "Pipeline completed, but no final output was designated or the final node produced no output.";
    }
}