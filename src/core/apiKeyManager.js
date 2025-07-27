// src/core/apiKeyManager.js

import { USER } from './manager.js';
import { renderSettings } from '../scripts/settings/userExtensionSetting.js';

// --- Key Status Enums ---
const KEY_STATUS = {
    HEALTHY: 'healthy',
    BANNED: 'banned',
    SUSPENDED: 'suspended'
};

const QUOTA_ERROR_LIMIT_PER_DAY = 5;

// --- 错误分类函数 ---
function getErrorType(error) {
    const message = error.message.toLowerCase();
    const status = error.message.match(/\[(\d{3})\]/)?.[1] || '';

    if (message.includes('api key not valid') || 
        message.includes('permission denied') || 
        message.includes('consumer suspended') ||
        message.includes('expired') ||
        (status === '403') ||
        (status === '400') // 将400作为API Key错误的强信号，因为它通常与请求格式或认证有关
    ) {
        return 'ApiKeyError';
    }
    if (status === '429' || message.includes('quota exceeded') || message.includes('rate limit exceeded')) {
        return 'QuotaError';
    }
    // [!code focus:start]
    // --- 新增：识别自定义的空响应错误 ---
    if (message.includes('emptyresponseerror') || status.startsWith('5') || message.includes('socket hang up') || message.includes('fetch failed')|| message.includes('prohibited')) {
        return 'NetworkError'; // 将空响应归类为网络/瞬时错误
    }
    // [!code focus:end]
    return 'UnknownError';
}

// ... ApiKeyManager 类的其余部分保持不变 ...
class ApiKeyManager {
    constructor() {
        this.keyPool = new Map(); // key -> { status: string, stats: object }
        this.busyKeys = new Set();
        this.waitQueue = [];
    }

    /**
     * 从用户设置加载或刷新API密钥池。
     */
    loadKeys() {
        const userKeys = USER.settings.geminiApiKeys || [];
        const today = new Date().toISOString().slice(0, 10);

        // 清理旧的key，保留已有的健康数据
        const newKeySet = new Set(userKeys);
        for (const key of this.keyPool.keys()) {
            if (!newKeySet.has(key)) {
                this.keyPool.delete(key);
            }
        }
        
        // 添加新key或更新现有key的状态
        userKeys.forEach(key => {
            if (key && key.trim() !== '') {
                if (!this.keyPool.has(key)) {
                    this.keyPool.set(key, {
                        status: KEY_STATUS.HEALTHY,
                        stats: {
                            lastErrorDate: '',
                            quotaErrorCount: 0,
                            networkErrorCount: 0,
                            suspensionEndTime: 0
                        }
                    });
                } else {
                    // 如果是新的一天，重置每日配额计数
                    const entry = this.keyPool.get(key);
                    if (entry.stats.lastErrorDate !== today) {
                        entry.stats.quotaErrorCount = 0;
                    }
                    // 如果停用时间已过，恢复健康状态
                    if (entry.status === KEY_STATUS.SUSPENDED && Date.now() > entry.stats.suspensionEndTime) {
                        entry.status = KEY_STATUS.HEALTHY;
                        entry.stats.suspensionEndTime = 0;
                        console.log(`[ApiKeyManager] Key ...${key.slice(-4)} has been restored from suspension.`);
                    }
                }
            }
        });

        console.log(`[ApiKeyManager] Loaded and synchronized ${this.keyPool.size} keys.`);
        this._processWaitQueue();
    }

    /**
     * 获取一个健康的、空闲的API密钥。
     * @returns {Promise<string|null>} 一个解析为可用密钥或null的Promise。
     */
    getHealthyKey() {
        // 每次获取时都刷新状态，确保及时恢复被暂停的key
        this.loadKeys(); 

        const healthyAndFreeKeys = Array.from(this.keyPool.entries())
            .filter(([key, data]) => 
                data.status === KEY_STATUS.HEALTHY && !this.busyKeys.has(key)
            );

        if (healthyAndFreeKeys.length > 0) {
            const [keyToUse] = healthyAndFreeKeys[0]; 
            this.busyKeys.add(keyToUse);
            console.log(`[ApiKeyManager] Acquired healthy key ...${keyToUse.slice(-4)}`);
            return Promise.resolve(keyToUse);
        }
        
        const healthyButBusy = Array.from(this.keyPool.entries())
            .some(([key, data]) => data.status === KEY_STATUS.HEALTHY && this.busyKeys.has(key));
            
        if (healthyButBusy) {
             console.log(`[ApiKeyManager] All healthy keys are busy. Request is now waiting.`);
             return new Promise(resolve => this.waitQueue.push(resolve));
        }

        return Promise.resolve(null);
    }

    /**
     * 报告一次失败，管理器将据此更新密钥状态。
     * @param {string} key - 失败的密钥。
     * @param {Error} error - 捕获到的错误对象。
     */
    async recordFailure(key, error) {
        if (!this.keyPool.has(key)) return;

        const entry = this.keyPool.get(key);
        const errorType = getErrorType(error);
        const today = new Date().toISOString().slice(0, 10);
        entry.stats.lastErrorDate = today;

        console.warn(`[ApiKeyManager] Failure recorded for key ...${key.slice(-4)}. Type: ${errorType}. Error: ${error.message}`);

        switch (errorType) {
            case 'ApiKeyError':
                entry.status = KEY_STATUS.BANNED;
                console.error(`[ApiKeyManager] Key ...${key.slice(-4)} has been permanently banned.`);
                toastr.error(`An API key (...${key.slice(-4)}) was found to be invalid/banned and has been permanently disabled.`, "API Key Banned");
                
                // [!code focus:start]
                // 【关键修正】我们应该直接在这里修改用户设置，而不是依赖下次loadKeys
                const currentKeys = USER.settings.geminiApiKeys || [];
                // 过滤掉当前坏掉的key
                const newKeys = currentKeys.filter(k => k !== key);
                // 确保 USER.settings.geminiApiKeys 被正确赋值以触发代理的set
                if (newKeys.length !== currentKeys.length) {
                    USER.settings.geminiApiKeys = newKeys;
                }

            case 'QuotaError':
                entry.stats.quotaErrorCount++;
                if (entry.stats.quotaErrorCount >= QUOTA_ERROR_LIMIT_PER_DAY) {
                    entry.status = KEY_STATUS.SUSPENDED;
                    const tomorrow = new Date();
                    tomorrow.setHours(24, 0, 0, 0); 
                    entry.stats.suspensionEndTime = tomorrow.getTime();
                    console.error(`[ApiKeyManager] Key ...${key.slice(-4)} has reached its daily quota limit and is suspended until tomorrow.`);
                    toastr.warning(`An API key (...${key.slice(-4)}) seems to have hit its daily limit. It will be temporarily disabled.`, "Key Suspended");
                }
                break;
                
            case 'NetworkError':
                entry.stats.networkErrorCount++;
                break;
        }
        
        this.releaseKey(key);
    }
    
    releaseKey(key) {
        if (key && this.busyKeys.has(key)) {
            this.busyKeys.delete(key);
            console.log(`[ApiKeyManager] Released key ...${key.slice(-4)}.`);
            this._processWaitQueue();
        }
    }

    _processWaitQueue() {
        if (this.waitQueue.length > 0) {
            const healthyAndFreeKeys = Array.from(this.keyPool.entries())
                .filter(([key, data]) => 
                    data.status === KEY_STATUS.HEALTHY && !this.busyKeys.has(key)
                );
            if (healthyAndFreeKeys.length > 0) {
                const [keyToUse] = healthyAndFreeKeys[0];
                const nextInQueue = this.waitQueue.shift();
                this.busyKeys.add(keyToUse);
                console.log(`[ApiKeyManager] Re-assigned key ...${keyToUse.slice(-4)} to waiting request.`);
                nextInQueue(keyToUse);
            }
        }
    }
}

export const apiKeyManager = new ApiKeyManager();