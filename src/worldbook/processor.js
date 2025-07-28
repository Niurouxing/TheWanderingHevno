// src/worldbook/processor.js

/**
 * 世界书处理器 - 实现关键词匹配、递归激活等核心逻辑
 */

// 常量定义
export const WORLD_INFO_LOGIC = {
    AND_ANY: 0,
    NOT_ALL: 1,
    NOT_ANY: 2,
    AND_ALL: 3,
};

export const WORLD_INFO_POSITION = {
    before: 0,
    after: 1,
    ANTop: 2,
    ANBottom: 3,
    atDepth: 4,
    EMTop: 5,
    EMBottom: 6,
};

export const DEFAULT_DEPTH = 4;
export const DEFAULT_BUDGET = 25; // 默认token预算（百分比）
export const MAX_RECURSION_DEPTH = 10;

/**
 * 世界书处理器类
 */
export class WorldInfoProcessor {
    constructor(options = {}) {
        this.options = {
            budget: options.budget || DEFAULT_BUDGET,
            maxRecursionDepth: options.maxRecursionDepth || MAX_RECURSION_DEPTH,
            caseSensitive: options.caseSensitive || false,
            matchWholeWords: options.matchWholeWords || false,
            includeNames: options.includeNames !== false, // 默认为true
            ...options
        };
        
        this.debugMode = options.debugMode || false;
    }

    /**
     * 处理世界书并返回激活的条目
     * @param {Object[]} entries - 世界书条目数组
     * @param {string[]} chatMessages - 聊天消息数组（倒序）
     * @param {Object} globalScanData - 全局扫描数据
     * @param {number} maxContext - 最大上下文长度
     * @returns {Promise<Object>} 处理结果
     */
    async processWorldInfo(entries, chatMessages, globalScanData = {}, maxContext = 4096) {
        console.log(`[WorldInfoProcessor] Processing ${entries.length} entries`);
        
        const activatedEntries = [];
        const processedEntries = new Set(); // 防止重复处理
        const recursionStack = new Set(); // 防止无限递归
        
        // 第一轮：处理常量条目和关键词匹配
        const initialActivated = await this._processInitialEntries(
            entries, 
            chatMessages, 
            globalScanData, 
            processedEntries
        );
        
        activatedEntries.push(...initialActivated);

        // 递归处理
        let currentDepth = 0;
        let hasNewActivations = true;
        
        while (hasNewActivations && currentDepth < this.options.maxRecursionDepth) {
            hasNewActivations = false;
            currentDepth++;
            
            console.log(`[WorldInfoProcessor] Recursion depth ${currentDepth}`);
            
            // 获取新激活内容的文本用于下一轮匹配
            const newContent = activatedEntries
                .filter(entry => !recursionStack.has(entry.uid))
                .map(entry => entry.content)
                .join(' ');
            
            if (!newContent.trim()) {
                break;
            }

            // 用新内容进行匹配
            const recursiveActivated = await this._processRecursiveEntries(
                entries,
                [newContent], // 将新内容作为"消息"进行匹配
                globalScanData,
                processedEntries,
                recursionStack
            );
            
            if (recursiveActivated.length > 0) {
                activatedEntries.push(...recursiveActivated);
                hasNewActivations = true;
                
                // 将新激活的条目加入递归栈
                recursiveActivated.forEach(entry => recursionStack.add(entry.uid));
            }
        }

        // 排序和格式化
        const sortedEntries = this._sortEntriesByOrder(activatedEntries);
        const formattedResult = this._formatActivatedEntries(sortedEntries, maxContext);
        
        console.log(`[WorldInfoProcessor] Activated ${activatedEntries.length} entries after ${currentDepth} recursion rounds`);
        
        return formattedResult;
    }

    /**
     * 处理初始条目（常量和关键词匹配）
     */
    async _processInitialEntries(entries, chatMessages, globalScanData, processedEntries) {
        const activated = [];
        
        for (const entry of entries) {
            if (processedEntries.has(entry.uid) || entry.disable) {
                continue;
            }

            // 检查概率
            if (entry.useProbability && entry.probability < 100) {
                const roll = Math.random() * 100;
                if (roll > entry.probability) {
                    if (this.debugMode) {
                        console.log(`[WorldInfoProcessor] Entry ${entry.uid} failed probability check (${roll.toFixed(1)} > ${entry.probability})`);
                    }
                    continue;
                }
            }

            let shouldActivate = false;

            // 常量条目始终激活
            if (entry.constant) {
                shouldActivate = true;
                if (this.debugMode) {
                    console.log(`[WorldInfoProcessor] Entry ${entry.uid} activated as constant`);
                }
            } else if (entry.key && entry.key.length > 0) {
                // 关键词匹配
                shouldActivate = this._checkKeywordMatch(entry, chatMessages, globalScanData);
                if (this.debugMode && shouldActivate) {
                    console.log(`[WorldInfoProcessor] Entry ${entry.uid} activated by keyword match`);
                }
            }

            if (shouldActivate) {
                activated.push(entry);
                processedEntries.add(entry.uid);
            }
        }

        return activated;
    }

    /**
     * 处理递归条目
     */
    async _processRecursiveEntries(entries, newContentArray, globalScanData, processedEntries, recursionStack) {
        const activated = [];
        
        for (const entry of entries) {
            if (processedEntries.has(entry.uid) || 
                entry.disable || 
                entry.constant || 
                entry.preventRecursion ||
                recursionStack.has(entry.uid)) {
                continue;
            }

            if (entry.key && entry.key.length > 0) {
                const shouldActivate = this._checkKeywordMatch(entry, newContentArray, {});
                if (shouldActivate) {
                    activated.push(entry);
                    processedEntries.add(entry.uid);
                    if (this.debugMode) {
                        console.log(`[WorldInfoProcessor] Entry ${entry.uid} activated by recursive match`);
                    }
                }
            }
        }

        return activated;
    }

    /**
     * 检查关键词匹配
     * @param {Object} entry - 世界书条目
     * @param {string[]} textArray - 要搜索的文本数组
     * @param {Object} globalScanData - 全局扫描数据
     * @returns {boolean} 是否匹配
     */
    _checkKeywordMatch(entry, textArray, globalScanData) {
        // 构建搜索文本
        let searchText = textArray.join(' ');
        
        // 根据条目设置添加全局数据
        if (entry.matchPersonaDescription && globalScanData.personaDescription) {
            searchText += ' ' + globalScanData.personaDescription;
        }
        if (entry.matchCharacterDescription && globalScanData.characterDescription) {
            searchText += ' ' + globalScanData.characterDescription;
        }
        if (entry.matchCharacterPersonality && globalScanData.characterPersonality) {
            searchText += ' ' + globalScanData.characterPersonality;
        }
        if (entry.matchScenario && globalScanData.scenario) {
            searchText += ' ' + globalScanData.scenario;
        }

        // 大小写处理
        const caseSensitive = entry.caseSensitive ?? this.options.caseSensitive;
        if (!caseSensitive) {
            searchText = searchText.toLowerCase();
        }

        if (this.debugMode) {
            console.log(`[WorldInfoProcessor] Checking entry ${entry.uid} keywords: [${entry.key?.join(', ') || 'none'}]`);
            console.log(`[WorldInfoProcessor] Search text length: ${searchText.length}, preview: "${searchText.substring(0, 100)}..."`);
        }

        // 主要关键词匹配
        const primaryMatches = this._checkKeyArray(entry.key, searchText, caseSensitive, entry.matchWholeWords);
        
        // 次要关键词匹配（如果有）
        let secondaryMatches = null; // 默认为null表示没有次要关键词
        if (entry.keysecondary && entry.keysecondary.length > 0) {
            secondaryMatches = this._checkKeyArray(entry.keysecondary, searchText, caseSensitive, entry.matchWholeWords);
        }

        // 根据选择性逻辑计算最终结果
        const finalResult = this._evaluateSelectiveLogic(entry.selectiveLogic, primaryMatches, secondaryMatches);
        
        if (this.debugMode) {
            console.log(`[WorldInfoProcessor] Entry ${entry.uid} match result: primary=${primaryMatches}, secondary=${secondaryMatches}, final=${finalResult}`);
        }
        
        return finalResult;
    }

    /**
     * 检查关键词数组
     * @param {string[]} keys - 关键词数组
     * @param {string} searchText - 搜索文本
     * @param {boolean} caseSensitive - 是否大小写敏感
     * @param {boolean} matchWholeWords - 是否匹配整词
     * @returns {boolean} 是否有匹配
     */
    _checkKeyArray(keys, searchText, caseSensitive, matchWholeWords) {
        if (!keys || keys.length === 0) {
            return false;
        }
        
        for (const key of keys) {
            if (!key || key.trim() === '') continue;
            
            let searchKey = caseSensitive ? key : key.toLowerCase();
            
            if (this.debugMode) {
                console.log(`[WorldInfoProcessor] Testing keyword: "${key}" (searchKey: "${searchKey}")`);
            }
            
            if (this._isRegexPattern(searchKey)) {
                // 正则表达式匹配
                try {
                    const regex = this._parseRegexFromString(searchKey);
                    if (regex && regex.test(searchText)) {
                        if (this.debugMode) {
                            console.log(`[WorldInfoProcessor] ✓ Regex match: "${key}"`);
                        }
                        return true;
                    }
                } catch (error) {
                    console.warn(`[WorldInfoProcessor] Invalid regex pattern: ${searchKey}`);
                    continue;
                }
            } else {
                // 普通文本匹配
                if (matchWholeWords ?? this.options.matchWholeWords) {
                    const wordRegex = new RegExp(`\\b${this._escapeRegex(searchKey)}\\b`, caseSensitive ? 'g' : 'gi');
                    if (wordRegex.test(searchText)) {
                        if (this.debugMode) {
                            console.log(`[WorldInfoProcessor] ✓ Whole word match: "${key}"`);
                        }
                        return true;
                    }
                } else {
                    if (searchText.includes(searchKey)) {
                        if (this.debugMode) {
                            console.log(`[WorldInfoProcessor] ✓ Substring match: "${key}"`);
                            // 显示匹配上下文
                            const index = searchText.indexOf(searchKey);
                            const context = searchText.substring(Math.max(0, index - 20), index + searchKey.length + 20);
                            console.log(`[WorldInfoProcessor] Match context: "...${context}..."`);
                        }
                        return true;
                    }
                }
            }
            
            if (this.debugMode) {
                console.log(`[WorldInfoProcessor] ❌ No match: "${key}"`);
            }
        }
        
        return false;
    }

    /**
     * 评估选择性逻辑
     * @param {number} logic - 逻辑类型
     * @param {boolean} primaryMatch - 主要关键词匹配结果
     * @param {boolean|null} secondaryMatch - 次要关键词匹配结果，null表示没有次要关键词
     * @returns {boolean} 最终匹配结果
     */
    _evaluateSelectiveLogic(logic, primaryMatch, secondaryMatch) {
        // 如果没有次要关键词，只考虑主要关键词
        if (secondaryMatch === null) {
            return primaryMatch;
        }
        
        switch (logic) {
            case WORLD_INFO_LOGIC.AND_ANY:
                return primaryMatch || secondaryMatch;
            case WORLD_INFO_LOGIC.AND_ALL:
                return primaryMatch && secondaryMatch;
            case WORLD_INFO_LOGIC.NOT_ALL:
                return !(primaryMatch && secondaryMatch);
            case WORLD_INFO_LOGIC.NOT_ANY:
                return !(primaryMatch || secondaryMatch);
            default:
                return primaryMatch;
        }
    }

    /**
     * 按顺序排序条目
     */
    _sortEntriesByOrder(entries) {
        return entries.sort((a, b) => {
            // 首先按order排序（降序）
            if (a.order !== b.order) {
                return b.order - a.order;
            }
            // 然后按uid排序
            return a.uid - b.uid;
        });
    }

    /**
     * 格式化激活的条目
     */
    _formatActivatedEntries(entries, maxContext) {
        const positionGroups = {
            before: [],
            after: [],
            ANTop: [],
            ANBottom: [],
            atDepth: [],
            EMTop: [],
            EMBottom: []
        };

        // 按位置分组
        for (const entry of entries) {
            const position = entry.position || WORLD_INFO_POSITION.before;
            const positionKey = Object.keys(WORLD_INFO_POSITION).find(key => 
                WORLD_INFO_POSITION[key] === position
            ) || 'before';
            
            if (positionGroups[positionKey]) {
                positionGroups[positionKey].push(entry);
            }
        }

        // 格式化内容
        const formatGroup = (group) => {
            return group.map(entry => entry.content).filter(content => content && content.trim()).join('\n\n');
        };

        return {
            worldInfoBefore: formatGroup(positionGroups.before),
            worldInfoAfter: formatGroup(positionGroups.after),
            ANTop: formatGroup(positionGroups.ANTop),
            ANBottom: formatGroup(positionGroups.ANBottom),
            atDepth: positionGroups.atDepth,
            EMTop: formatGroup(positionGroups.EMTop),
            EMBottom: formatGroup(positionGroups.EMBottom),
            allActivatedEntries: entries,
            worldInfoString: formatGroup(entries) // 所有内容的合并
        };
    }

    /**
     * 检查是否为正则表达式模式
     */
    _isRegexPattern(str) {
        return str.startsWith('/') && str.lastIndexOf('/') > 0;
    }

    /**
     * 解析正则表达式字符串
     */
    _parseRegexFromString(regexStr) {
        const lastSlash = regexStr.lastIndexOf('/');
        if (lastSlash <= 0) return null;
        
        const pattern = regexStr.slice(1, lastSlash);
        const flags = regexStr.slice(lastSlash + 1);
        
        try {
            return new RegExp(pattern, flags);
        } catch (error) {
            return null;
        }
    }

    /**
     * 转义正则表达式特殊字符
     */
    _escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}
