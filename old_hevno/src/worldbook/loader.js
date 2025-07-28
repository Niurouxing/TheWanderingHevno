// src/worldbook/loader.js

import { stIntegration } from './st-integration.js';

/**
 * 世界书加载器 - 负责从SillyTavern系统加载世界书数据
 * 【修正版】使用高级集成方法绕过HTTP API限制，不使用备用数据
 */
export class WorldInfoLoader {
    constructor() {
        this.cache = new Map(); // 简单的内存缓存
    }

    /**
     * 加载指定名称的世界书
     * @param {string} worldName - 世界书名称（不含扩展名）
     * @returns {Promise<Object|null>} 世界书数据或null（如果不存在）
     */
    async loadWorldInfo(worldName) {
        // 检查缓存
        if (this.cache.has(worldName)) {
            console.log(`[WorldInfoLoader] Loading ${worldName} from cache`);
            return this.cache.get(worldName);
        }

        try {
            console.log(`[WorldInfoLoader] Loading world info: ${worldName}`);
            
            // 【修正】使用高级集成方法获取世界书数据
            const worldData = await stIntegration.getWorldInfo(worldName);
            
            if (!worldData) {
                console.error(`[WorldInfoLoader] Failed to load world info: ${worldName}`);
                console.error(`[WorldInfoLoader] All integration methods failed. Check SillyTavern permissions and file paths.`);
                return null;
            }
            
            // 验证数据结构
            if (!worldData.entries || typeof worldData.entries !== 'object') {
                console.error(`[WorldInfoLoader] Invalid world info structure in ${worldName}: missing entries`);
                return null;
            }

            // 转换为数组格式以便处理
            const entries = Object.values(worldData.entries).map(entry => ({
                ...entry,
                worldName: worldName // 添加来源标识
            }));

            const processedData = {
                name: worldName,
                entries: entries,
                metadata: worldData.metadata || {}
            };

            // 缓存数据
            this.cache.set(worldName, processedData);
            
            console.log(`[WorldInfoLoader] Successfully loaded ${entries.length} entries from ${worldName}`);
            return processedData;
            
        } catch (error) {
            console.error(`[WorldInfoLoader] Error loading world info ${worldName}:`, error);
            return null;
        }
    }

    /**
     * 批量加载多个世界书
     * @param {string[]} worldNames - 世界书名称数组
     * @returns {Promise<Object[]>} 加载成功的世界书数据数组
     */
    async loadMultipleWorldInfo(worldNames) {
        const results = [];
        
        for (const worldName of worldNames) {
            const worldData = await this.loadWorldInfo(worldName);
            if (worldData) {
                results.push(worldData);
            }
        }

        return results;
    }

    /**
     * 获取所有已加载世界书的条目，合并为单一数组
     * @param {string[]} worldNames - 要包含的世界书名称
     * @returns {Promise<Object[]>} 合并后的条目数组
     */
    async getAllEntries(worldNames) {
        const worlds = await this.loadMultipleWorldInfo(worldNames);
        const allEntries = [];

        for (const world of worlds) {
            allEntries.push(...world.entries);
        }

        console.log(`[WorldInfoLoader] Collected ${allEntries.length} total entries from ${worlds.length} worlds`);
        return allEntries;
    }

    /**
     * 清理缓存
     */
    clearCache() {
        this.cache.clear();
        stIntegration.clearCache();
        console.log('[WorldInfoLoader] Cache cleared');
    }

    /**
     * 获取可用的世界书列表
     * @returns {Promise<string[]>} 可用的世界书名称数组
     */
    async getAvailableWorlds() {
        try {
            return await stIntegration.getAvailableWorlds();
        } catch (error) {
            console.error('[WorldInfoLoader] Error getting available worlds:', error);
            return ['world_info', 'character_info']; // 最小化的备用列表
        }
    }
}

// 创建默认实例
export const worldInfoLoader = new WorldInfoLoader();
