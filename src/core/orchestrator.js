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
        // 1. 如果模块没有配置World Info，则提前返回，避免不必要的操作。
        if (!module.worldInfo || !Array.isArray(module.worldInfo) || module.worldInfo.length === 0) {
            return '';
        }

        // 2. 【核心逻辑】在进入 try 块之前，完整地备份 SillyTavern 的当前状态。
        //    使用扩展运算符 `...` 和 `JSON.parse(JSON.stringify(...))` 来创建深/浅副本，
        //    防止后续操作意外修改原始备份。
        const originalState = {
            selected_world_info: window.selected_world_info ? [...window.selected_world_info] : [],
            characters: window.characters ? [...window.characters] : [],
            chat_metadata: window.chat_metadata ? JSON.parse(JSON.stringify(window.chat_metadata)) : {},
            power_user_lorebook: window.power_user?.persona_description_lorebook
        };

        try {
            // 3. 检查必要的SillyTavern函数是否存在。
            if (typeof SYSTEM.getWorldInfoPrompt !== 'function' || typeof SYSTEM.loadWorldInfo !== 'function') {
                console.error('[Orchestrator] World Info functions are not available in the SYSTEM manager.');
                return ''; // 返回安全值
            }

            console.log(`[Orchestrator] Temporarily setting module WI: [${module.worldInfo.join(', ')}]`);

            // 4. 修改全局状态，为模块的WI计算做准备。
            //    这里清空了全局的WI选择、角色列表、聊天元数据，并禁用了角色的默认lorebook，
            //    以确保一个“干净”的计算环境。
            if (!window.selected_world_info) window.selected_world_info = [];
            window.selected_world_info.length = 0;
            window.selected_world_info.push(...module.worldInfo);

            if (!window.characters) window.characters = [];
            window.characters.length = 0;
            
            if (!window.chat_metadata) window.chat_metadata = {};
            Object.keys(window.chat_metadata).forEach(key => delete window.chat_metadata[key]);
            
            if (!window.power_user) window.power_user = {};
            window.power_user.persona_description_lorebook = undefined;

            // 5. 异步加载模块指定的WI文件。
            const loadPromises = module.worldInfo.map(worldName => SYSTEM.loadWorldInfo(worldName));
            await Promise.all(loadPromises);

            // 6. 准备参数并调用SillyTavern的核心WI计算函数。
            const chatMessages = this.rawContext.chat
                .filter(m => !m.is_system)
                .map(m => m.mes)
                .reverse();
            const maxContextSize = this.rawContext.max_context || 4096;
            const globalScanData = { /* ... 保持与原代码一致 ... */ };

            console.log(`[Orchestrator] Calling getWorldInfoPrompt for module...`);
            const wiResult = await SYSTEM.getWorldInfoPrompt(chatMessages, maxContextSize, true, globalScanData);

            const moduleWiString = (wiResult?.worldInfoString || wiResult || '').toString().trim();
            console.log(`[Orchestrator] Module WI calculated. Length: ${moduleWiString.length}`);

            // 7. 返回计算结果。
            return moduleWiString;

        } catch (error) {
            // 8. 如果在 try 块中发生任何错误，捕获它，记录日志，并返回一个安全的空字符串。
            console.error(`[Orchestrator] An error occurred during module WI calculation:`, error);
            return '';
        } finally {
            // 9. 【关键修正】无论 try 块是成功还是失败，此处的代码都将保证执行。
            console.log('[Orchestrator] Restoring original SillyTavern state...');

            // 恢复所有被修改的全局变量到它们被修改之前的状态。
            window.selected_world_info.length = 0;
            window.selected_world_info.push(...originalState.selected_world_info);

            window.characters.length = 0;
            window.characters.push(...originalState.characters);

            Object.keys(window.chat_metadata).forEach(key => delete window.chat_metadata[key]);
            Object.assign(window.chat_metadata, originalState.chat_metadata);

            if (originalState.power_user_lorebook !== undefined) {
                window.power_user.persona_description_lorebook = originalState.power_user_lorebook;
            }

            console.log('[Orchestrator] Original state restored successfully.');
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
        this.context.module = { worldInfo: '' };
        const promptForWiScan = this._renderPrompt(node, node.injectedParams);
        this.context.module.worldInfo = await this._calculateModuleWorldInfo(node, promptForWiScan);

        const finalPrompt = this._renderPrompt(node, node.injectedParams);
        console.log(`[Orchestrator] === START LLM PROMPT for ${node.id} ===\n${finalPrompt}\n=== END LLM PROMPT for ${node.id} ===`);

        const result = await dispatchLLM(finalPrompt, node.llm);

        console.log(`[Orchestrator] === START LLM OUTPUT for ${node.id} ===\n${result}\n=== END LLM OUTPUT for ${node.id} ===`);

        // 【新增】如果输出为空，给一个默认值防止后续模板渲染出错
        // 有些模型在某些情况下可能返回空字符串或null
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