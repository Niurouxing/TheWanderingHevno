// src/core/apiKeyManager.js 

import { USER } from './manager.js';

class ApiKeyManager {
    constructor() {
        this.keys = [];
        this.busyKeys = new Set();
        // 【新增】等待队列，存放Promise的resolve函数
        this.waitQueue = []; 
    }

    /**
     * 从用户设置加载或刷新API密钥列表。
     */
    loadKeys() {
        const userKeys = USER.settings.geminiApiKeys || [];
        this.keys = userKeys.filter(key => key && key.trim() !== '');
        console.log(`[ApiKeyManager] Loaded ${this.keys.length} Gemini API keys.`);
        // 【新增】如果密钥池变小，可能需要处理正在进行的请求，但简单起见，这里只重新加载
        // 如果有正在等待的请求，并且现在有新密钥可用，可以尝试处理它们
        this._processWaitQueue(); 
    }

    /**
     * 【重大修改】获取一个可用的API密钥，如果不可用则异步等待。
     * @returns {Promise<string>} 一个解析为可用API密钥的Promise。
     * @throws {Error} 如果没有配置任何密钥。
     */
    acquireKey() {
        if (this.keys.length === 0) {
            // 这是唯一应该立即抛出错误的地方
            return Promise.reject(new Error("No Gemini API keys are configured."));
        }

        // 寻找一个空闲的key
        const availableKey = this.keys.find(key => !this.busyKeys.has(key));

        if (availableKey) {
            this.busyKeys.add(availableKey);
            console.log(`[ApiKeyManager] Acquired key ending in ...${availableKey.slice(-4)}`);
            // 如果有可用key，立即返回一个已解决的Promise
            return Promise.resolve(availableKey);
        } else {
            // 如果没有可用key，返回一个新的Promise并进入等待队列
            console.log(`[ApiKeyManager] All keys are busy. Request is now waiting.`);
            return new Promise((resolve) => {
                this.waitQueue.push(resolve);
            });
        }
    }

    /**
     * 【重大修改】释放一个API密钥，并检查是否有等待的请求。
     * @param {string} key 要释放的API密钥。
     */
    releaseKey(key) {
        if (key && this.busyKeys.has(key)) {
            this.busyKeys.delete(key);
            console.log(`[ApiKeyManager] Released key ending in ...${key.slice(-4)}`);
            // 密钥已释放，检查等待队列
            this._processWaitQueue();
        }
    }
    
    /**
     * 【新增】内部辅助函数，用于处理等待队列。
     * @private
     */
    _processWaitQueue() {
        // 如果有等待的请求，并且有空闲的密钥
        if (this.waitQueue.length > 0) {
             const availableKey = this.keys.find(key => !this.busyKeys.has(key));
             if (availableKey) {
                console.log(`[ApiKeyManager] A key is now free. Fulfilling a waiting request.`);
                // 取出队列中最早的等待者
                const nextInQueue = this.waitQueue.shift();
                
                // 将可用的key标记为繁忙
                this.busyKeys.add(availableKey);
                console.log(`[ApiKeyManager] Re-assigned key ending in ...${availableKey.slice(-4)} to waiting request.`);
                
                // 解决它的Promise，并把key传给它
                nextInQueue(availableKey);
             }
        }
    }
}

// 导出单例，确保整个插件共享同一个密钥管理器
export const apiKeyManager = new ApiKeyManager();