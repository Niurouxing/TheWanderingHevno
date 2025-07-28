// src/core/orchestrator.js

import { dispatch as dispatchLLM } from './llm_dispatcher.js';
import { executeFunction } from './function_registry.js';
import { APP, SYSTEM } from './manager.js';
import { worldInfoManager } from '../worldbook/index.js';

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



    async _calculateModuleWorldInfo(module) {
        // 步骤 1: 如果节点没有配置World Info，直接返回空对象
        if (!module.worldInfo || !Array.isArray(module.worldInfo) || module.worldInfo.length === 0) {
            return this._createEmptyWorldInfoResult();
        }

        console.log(`[Orchestrator] Processing World Info for node: ${module.id}. Books: [${module.worldInfo.join(', ')}]`);

        try {
            // 临时设置一个空的worldInfo对象，防止在渲染过程中出现路径解析错误
            const originalModuleContext = this.context.module;
            this.context.module = { 
                ...originalModuleContext,
                worldInfo: this._createEmptyWorldInfoObject()
            };
            
            // 先渲染节点的prompt内容（不包含worldInfo），获取完整的渲染后文本
            // 这样可以包含所有用户想要的模板变量，如 {{item}}, {{outputs.story_generator}} 等
            const renderedPrompt = this._renderPrompt(module, module.injectedParams || {});
            
            // 恢复原始的module上下文
            this.context.module = originalModuleContext;
            
            console.log(`[Orchestrator] Using rendered prompt as search text for World Info (length: ${renderedPrompt.length})`);
            
            // 使用渲染后的prompt作为搜索文本（这是关键改进）
            const searchMessages = [renderedPrompt];
            
            const globalScanData = {
                personaDescription: this.rawContext.persona?.description ?? '',
                characterDescription: this.context.sillyTavern.character?.description ?? '',
                characterPersonality: this.context.sillyTavern.character?.personality ?? '',
                characterDepthPrompt: this.context.sillyTavern.character?.depth_prompt ?? '',
                scenario: this.rawContext.scenario ?? '',
                creatorNotes: this.context.sillyTavern.character?.creator_notes ?? '',
                userInput: this.context.sillyTavern.userInput ?? '',
            };

            // 使用新的世界书管理器计算世界书内容
            const worldInfoResult = await worldInfoManager.getWorldInfoPrompt(
                module.worldInfo,
                searchMessages, // 使用渲染后的prompt作为搜索文本
                globalScanData,
                this.rawContext.max_context || 4096
            );

            if (worldInfoResult.worldInfoString?.trim()) {
                console.log(`[Orchestrator] Node ${module.id} generated ${worldInfoResult.worldInfoString.length} chars of WI from ${worldInfoResult.allActivatedEntries.length} activated entries.`);
            } else {
                console.warn(`[Orchestrator] Node ${module.id} generated no WI with books [${module.worldInfo.join(', ')}]`);
            }

            return worldInfoResult;

        } catch (error) {
            console.error(`[Orchestrator] Error calculating World Info for node ${module.id}:`, error);
            return this._createEmptyWorldInfoResult();
        }
    }

    /**
     * 创建空的世界书结果对象
     */
    _createEmptyWorldInfoResult() {
        return {
            worldInfoBefore: '',
            worldInfoAfter: '',
            ANTop: '',
            ANBottom: '',
            atDepth: [],
            EMTop: '',
            EMBottom: '',
            allActivatedEntries: [],
            worldInfoString: ''
        };
    }

    /**
     * 创建空的世界书对象（用于模板渲染时的临时占位）
     */
    _createEmptyWorldInfoObject() {
        const worldInfoObject = Object.create(String.prototype);
        Object.assign(worldInfoObject, {
            // 作为字符串时的值
            toString: () => '',
            valueOf: () => '',
            
            // 分位置的属性
            before: '',
            after: '',
            ANTop: '',
            ANBottom: '',
            EMTop: '',
            EMBottom: '',
            atDepth: []
        });
        return worldInfoObject;
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
            if (params.sourceMapNode && this.nodes[params.sourceMapNode]) {
                nodeDependencies.add(params.sourceMapNode);
                // 【关键修改】标记这个节点需要等待Map节点的动态子节点完成
                node._waitForMapCompletion = params.sourceMapNode;
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

            // 路由器的分支目标依赖于路由器本身
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
        const nodeLabel = `${node.id} (${node.name})`;
        console.log(`[Pipeline] 🎯 Executing LLM node: ${nodeLabel}`);
        
        // 计算世界书信息 - 现在返回完整的结果对象
        const worldInfoResult = await this._calculateModuleWorldInfo(node);
        
        // 设置世界书模块上下文，支持分位置访问
        // 创建一个特殊的worldInfo对象，既可以作为字符串使用，也可以访问嵌套属性
        const worldInfoObject = Object.create(String.prototype);
        Object.assign(worldInfoObject, {
            // 作为字符串时的值
            toString: () => worldInfoResult.worldInfoString || '',
            valueOf: () => worldInfoResult.worldInfoString || '',
            
            // 分位置的属性
            before: worldInfoResult.worldInfoBefore || '',
            after: worldInfoResult.worldInfoAfter || '',
            ANTop: worldInfoResult.ANTop || '',
            ANBottom: worldInfoResult.ANBottom || '',
            EMTop: worldInfoResult.EMTop || '',
            EMBottom: worldInfoResult.EMBottom || '',
            atDepth: worldInfoResult.atDepth || []
        });
        
        this.context.module = { 
            worldInfo: worldInfoObject
        };
        
        const finalPrompt = this._renderPrompt(node, node.injectedParams);

        // =================== 详细的LLM调用预览 ===================
        console.log(`[Pipeline] ================== LLM CALL OVERVIEW: ${nodeLabel} ==================`);
        console.log(`[Pipeline] � Node: ${nodeLabel}`);
        console.log(`[Pipeline] 🤖 Model: ${node.llm.provider}/${node.llm.model}`);
        console.log(`[Pipeline] ⚙️  Config:`, {
            temperature: node.llm.temperature,
            maxOutputTokens: node.llm.maxOutputTokens,
            topP: node.llm.topP
        });
        console.log(`[Pipeline] 📏 Prompt Length: ${finalPrompt.length} characters`);
        console.log(`[Pipeline] 🌍 World Info Length: ${worldInfoResult.worldInfoString ? worldInfoResult.worldInfoString.length : 0} characters`);
        console.log(`[Pipeline] ⏰ Timestamp: ${new Date().toISOString()}`);
        console.log(`[Pipeline] 📝 Full Prompt:`);
        console.log(finalPrompt);
        console.log(`[Pipeline] ================== PROMPT END ==================`);

        try {
            const startTime = Date.now();
            const result = await dispatchLLM(finalPrompt, node.llm);
            const duration = Date.now() - startTime;

            // =================== 详细的LLM响应报告 ===================
            console.log(`[Pipeline] ================== LLM RESPONSE REPORT: ${nodeLabel} ==================`);
            console.log(`[Pipeline] 📋 Node: ${nodeLabel}`);
            console.log(`[Pipeline] ⏱️  Duration: ${duration}ms`);
            console.log(`[Pipeline] 📏 Response Length: ${result ? result.length : 0} characters`);
            
            if (!result || result.trim().length === 0) {
                console.warn(`[Pipeline] ⚠️  WARNING: EMPTY RESPONSE`);
                console.warn(`[Pipeline] 🔍 Check detailed API analysis above for diagnostic information`);
                console.log(`[Pipeline] 📝 Response Content: (EMPTY)`);
            } else {
                console.log(`[Pipeline] ✅ Success: Generated ${result.length} characters`);
                console.log(`[Pipeline] 📝 Full Response:`);
                console.log(result);
            }
            
            console.log(`[Pipeline] ================== RESPONSE END ==================`);

            return result || '';
            
        } catch (error) {
            console.error(`[Pipeline] ================== LLM ERROR REPORT: ${nodeLabel} ==================`);
            console.error(`[Pipeline] ❌ Error: ${error.message}`);
            console.error(`[Pipeline] 🔍 Full Error:`, error);
            console.error(`[Pipeline] ================== ERROR END ==================`);
            throw error;
        }
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

        if (!Array.isArray(list) || list.length === 0) {
            console.warn(`[MapNode:${node.id}] Input list is empty or not an array.`);
            // Map节点的输出是空数组
            this.context.outputs[node.id] = [];
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

        // Map节点的输出是动态节点ID的列表
        this.context.outputs[node.id] = dynamicNodeIds;
        console.log(`[MapNode:${node.id}] Output: [${dynamicNodeIds.join(', ')}]`);
        
        // 【关键修改】Map节点现在不立即完成，而是等待所有动态节点完成
        // 这将在主执行循环中的检查逻辑中处理
        console.log(`[MapNode:${node.id}] Waiting for ${dynamicNodeIds.length} dynamic nodes to complete...`);
    }

    async run() {
        console.log('[Orchestrator V2] Starting dynamic graph execution...');
        this._initializeGraph();

        const inDegree = new Map();
        for (const nodeId in this.nodes) {
            const baseDegree = this.dependencies.get(nodeId)?.size || 0;
            const node = this.nodes[nodeId];
            
            // 【新增】如果节点需要等待Map完成，增加额外的入度
            let finalDegree = baseDegree;
            if (node._waitForMapCompletion) {
                finalDegree += 1; // 额外增加1个入度，直到Map真正完成才减少
                console.log(`[GraphInit] Node ${nodeId} waiting for Map completion: ${node._waitForMapCompletion}, degree: ${baseDegree} -> ${finalDegree}`);
            }
            
            inDegree.set(nodeId, finalDegree);
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
                    
                    // 【关键修改】Map节点执行后保持running状态，等待动态节点完成
                    const node = this.nodes[nodeId];
                    if (node.type === 'map') {
                        // Map节点保持running状态，将在后续逻辑中检查并完成
                        console.log(`[MapNode:${nodeId}] Execution completed but staying in running state`);
                    } else {
                        this.nodeStates[nodeId] = 'completed';
                    }
                } catch (error) {
                    this.nodeStates[nodeId] = 'failed';
                    const nodeName = this.nodes[nodeId]?.name || 'Unknown Node';
                    console.error(`Execution failed at node ${nodeName} (${nodeId}):`, error);
                    // 抛出错误以停止整个流程
                    throw new Error(`Execution failed at node ${nodeName}: ${error.message}`);
                }
            });

            await Promise.all(promises);

            let nodesToProcessForDependents = new Set(currentBatch);

            // [!code focus:start]
            // ========================= 核心修正逻辑 START =========================
            // 处理Map节点创建的动态节点
            for (const completedNodeId of currentBatch) {
                const node = this.nodes[completedNodeId];
                if (node.type === 'map' && this.nodeStates[completedNodeId] === 'running') {
                    const dynamicNodeIds = this.context.outputs[completedNodeId] || [];
                    
                    // 为新创建的动态节点设置入度并加入队列
                    for (const dynamicNodeId of dynamicNodeIds) {
                        if (!inDegree.has(dynamicNodeId)) {
                            const initialDegree = this.dependencies.get(dynamicNodeId)?.size || 0;
                            inDegree.set(dynamicNodeId, initialDegree);
                            
                            // 如果入度为0（不太可能，因为动态节点依赖Map节点），加入队列
                            if (initialDegree === 0) {
                                executionQueue.push(dynamicNodeId);
                            }
                        }
                    }
                }
            }
            
            // 检查是否有Map节点的所有动态子节点都已完成
            for (const nodeId in this.nodes) {
                const node = this.nodes[nodeId];
                if (node.type === 'map' && this.nodeStates[nodeId] === 'running') {
                    // 检查这个Map节点的所有动态子节点是否都完成了
                    const dynamicNodeIds = this.context.outputs[nodeId] || [];
                    const allDynamicNodesCompleted = dynamicNodeIds.every(dynamicId => 
                        this.nodeStates[dynamicId] === 'completed' || 
                        this.nodeStates[dynamicId] === 'failed' || 
                        this.nodeStates[dynamicId] === 'skipped'
                    );
                    
                    if (allDynamicNodesCompleted && dynamicNodeIds.length > 0) {
                        // Map节点现在可以标记为完成
                        this.nodeStates[nodeId] = 'completed';
                        nodesToProcessForDependents.add(nodeId);
                        console.log(`[MapNode:${nodeId}] All ${dynamicNodeIds.length} dynamic nodes completed, Map node now completed`);
                        
                        // 【新增】检查是否有节点在等待这个Map节点的完全完成
                        for (const waitingNodeId in this.nodes) {
                            const waitingNode = this.nodes[waitingNodeId];
                            if (waitingNode._waitForMapCompletion === nodeId && this.nodeStates[waitingNodeId] === 'pending') {
                                // 减少这个等待节点的入度，因为它现在可以执行了
                                const currentDegree = inDegree.get(waitingNodeId) || 1;
                                const newDegree = currentDegree - 1;
                                inDegree.set(waitingNodeId, newDegree);
                                console.log(`[MapCompletion:${nodeId}] Releasing waiting node ${waitingNodeId}, degree: ${currentDegree} -> ${newDegree}`);
                                
                                // 重新检查该节点是否可以加入执行队列
                                if (newDegree === 0) {
                                    executionQueue.push(waitingNodeId);
                                    console.log(`[MapCompletion:${nodeId}] Added ${waitingNodeId} to execution queue`);
                                }
                            }
                        }
                    }
                }
            }
            // ========================= 核心修正逻辑 END =========================
            // [!code focus:end]

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