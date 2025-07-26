// src/core/apiKeyManager.js

import { USER } from './manager.js';

class ApiKeyManager {
    constructor() {
        this.keys = [];
        this.busyKeys = new Set();
        this.lastUsedIndex = -1;
    }

    /**
     * 从用户设置加载或刷新API密钥列表。
     */
    loadKeys() {
        const userKeys = USER.settings.geminiApiKeys || [];
        this.keys = userKeys.filter(key => key && key.trim() !== ''); // 过滤掉空密钥
        console.log(`[ApiKeyManager] Loaded ${this.keys.length} Gemini API keys.`);
    }

    /**
     * 获取一个可用的API密钥。
     * 实现简单的轮询和负载均衡。
     * @returns {string} 可用的API密钥。
     * @throws {Error} 如果没有可用的密钥。
     */
    acquireKey() {
        if (this.keys.length === 0) {
            throw new Error("No Gemini API keys are configured.");
        }
        if (this.busyKeys.size >= this.keys.length) {
            throw new Error("All Gemini API keys are currently in use. Please wait.");
        }

        // 轮询查找下一个可用密钥
        for (let i = 0; i < this.keys.length; i++) {
            this.lastUsedIndex = (this.lastUsedIndex + 1) % this.keys.length;
            const key = this.keys[this.lastUsedIndex];
            if (!this.busyKeys.has(key)) {
                this.busyKeys.add(key);
                console.log(`[ApiKeyManager] Acquired key ending in ...${key.slice(-4)}`);
                return key;
            }
        }
        
        // 理论上不应该到达这里，因为前面已经检查过 busyKeys.size
        throw new Error("Failed to acquire a key despite some being available. Concurrency issue?");
    }

    /**
     * 释放一个API密钥，使其可用于其他调用。
     * @param {string} key 要释放的API密钥。
     */
    releaseKey(key) {
        if (key && this.busyKeys.has(key)) {
            this.busyKeys.delete(key);
            console.log(`[ApiKeyManager] Released key ending in ...${key.slice(-4)}`);
        }
    }
}

// 导出单例，确保整个插件共享同一个密钥管理器
export const apiKeyManager = new ApiKeyManager();