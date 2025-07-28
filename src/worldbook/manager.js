// src/worldbook/manager.js

import { worldInfoLoader } from './loader.js';
import { WorldInfoProcessor } from './processor.js';

/**
 * 世界书管理器 - 提供高级API来处理世界书
 */
export class WorldInfoManager {
    constructor(options = {}) {
        this.loader = worldInfoLoader;
        
        // 默认配置，重点关注递归相关设置
        const defaultOptions = {
            budget: 25,                // token预算（百分比）
            maxRecursionDepth: 2,      // 【重要】最大递归深度，默认2次
            caseSensitive: false,      // 大小写敏感
            matchWholeWords: false,    // 匹配整词
            includeNames: true,        // 包含名称
            debugMode: true,           // 启用调试模式以诊断关键词匹配问题
            ...options
        };
        
        this.processor = new WorldInfoProcessor(defaultOptions);
        this.debugMode = defaultOptions.debugMode;
        
        if (this.debugMode) {
            console.log('[WorldInfoManager] Initialized with options:', defaultOptions);
        }
    }

    /**
     * 获取世界书提示内容
     * @param {string[]} worldNames - 要使用的世界书名称数组
     * @param {string[]} chatMessages - 聊天消息数组（倒序）
     * @param {Object} globalScanData - 全局扫描数据
     * @param {number} maxContext - 最大上下文长度
     * @returns {Promise<Object>} 世界书处理结果
     */
    async getWorldInfoPrompt(worldNames, chatMessages, globalScanData = {}, maxContext = 4096) {
        try {
            console.log(`[WorldInfoManager] Processing world info for books: [${worldNames.join(', ')}]`);
            
            // 加载所有世界书条目
            let allEntries = [];
            try {
                allEntries = await this.loader.getAllEntries(worldNames);
            } catch (loaderError) {
                console.error('[WorldInfoManager] Error loading world info entries:', loaderError);
                
                // 尝试逐个加载
                for (const worldName of worldNames) {
                    try {
                        const worldData = await this.loader.loadWorldInfo(worldName);
                        if (worldData && worldData.entries) {
                            allEntries.push(...worldData.entries);
                        } else {
                            console.error(`[WorldInfoManager] Failed to load ${worldName}: No data returned`);
                        }
                    } catch (singleLoadError) {
                        console.error(`[WorldInfoManager] Failed to load ${worldName}:`, singleLoadError);
                    }
                }
            }
            
            if (allEntries.length === 0) {
                console.error('[WorldInfoManager] No entries found in specified world books');
                console.error(`[WorldInfoManager] Failed to load any world books: [${worldNames.join(', ')}]`);
                // 返回空结果，但不隐藏错误
                return this._createEmptyResult('Failed to load world info - check SillyTavern configuration and world book files');
            }

            console.log(`[WorldInfoManager] Successfully loaded ${allEntries.length} world info entries`);

            // 处理世界书
            const result = await this.processor.processWorldInfo(
                allEntries,
                chatMessages,
                globalScanData,
                maxContext
            );

            if (this.debugMode) {
                console.log('[WorldInfoManager] Final result:', result);
            }

            return result;
            
        } catch (error) {
            console.error('[WorldInfoManager] Error processing world info:', error);
            return this._createEmptyResult();
        }
    }

    /**
     * 简化的接口：只返回主要的世界书字符串
     * @param {string[]} worldNames - 要使用的世界书名称数组
     * @param {string[]} chatMessages - 聊天消息数组
     * @param {Object} globalScanData - 全局扫描数据
     * @returns {Promise<string>} 世界书内容字符串
     */
    async getWorldInfoString(worldNames, chatMessages, globalScanData = {}) {
        const result = await this.getWorldInfoPrompt(worldNames, chatMessages, globalScanData);
        return result.worldInfoString || '';
    }

    /**
     * 获取可用的世界书列表
     * @returns {Promise<string[]>} 可用的世界书名称数组
     */
    async getAvailableWorlds() {
        return await this.loader.getAvailableWorlds();
    }

    /**
     * 预加载指定的世界书到缓存
     * @param {string[]} worldNames - 要预加载的世界书名称数组
     * @returns {Promise<boolean>} 是否成功预加载所有世界书
     */
    async preloadWorlds(worldNames) {
        try {
            const results = await this.loader.loadMultipleWorldInfo(worldNames);
            const successCount = results.length;
            const totalCount = worldNames.length;
            
            console.log(`[WorldInfoManager] Preloaded ${successCount}/${totalCount} world books`);
            return successCount === totalCount;
            
        } catch (error) {
            console.error('[WorldInfoManager] Error preloading worlds:', error);
            return false;
        }
    }

    /**
     * 清理缓存
     */
    clearCache() {
        this.loader.clearCache();
        console.log('[WorldInfoManager] Cache cleared');
    }

    /**
     * 更新处理器选项
     * @param {Object} options - 新的选项
     */
    updateOptions(options) {
        this.processor = new WorldInfoProcessor({
            ...this.processor.options,
            ...options
        });
        this.debugMode = options.debugMode !== undefined ? options.debugMode : this.debugMode;
        console.log('[WorldInfoManager] Options updated:', options);
    }

    /**
     * 获取世界书条目详情（用于调试）
     * @param {string} worldName - 世界书名称
     * @returns {Promise<Object|null>} 世界书详情
     */
    async getWorldDetails(worldName) {
        return await this.loader.loadWorldInfo(worldName);
    }

    /**
     * 测试关键词匹配（用于调试）
     * @param {string} worldName - 世界书名称
     * @param {string} testText - 测试文本
     * @returns {Promise<Object[]>} 匹配的条目
     */
    async testKeywordMatch(worldName, testText) {
        const worldData = await this.loader.loadWorldInfo(worldName);
        if (!worldData) {
            return [];
        }

        const matches = [];
        for (const entry of worldData.entries) {
            if (entry.disable || !entry.key || entry.key.length === 0) {
                continue;
            }

            const isMatch = this.processor._checkKeywordMatch(entry, [testText], {});
            if (isMatch) {
                matches.push({
                    uid: entry.uid,
                    comment: entry.comment,
                    keys: entry.key,
                    content: entry.content.substring(0, 100) + (entry.content.length > 100 ? '...' : '')
                });
            }
        }

        return matches;
    }

    /**
     * 创建空结果
     * @private
     * @param {string} reason - 可选的原因说明
     */
    _createEmptyResult(reason = '') {
        if (reason) {
            console.log(`[WorldInfoManager] Creating empty result: ${reason}`);
        }
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
}

// 创建默认实例
export const worldInfoManager = new WorldInfoManager();
