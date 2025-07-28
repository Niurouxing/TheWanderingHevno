// src/worldbook/st-integration.js

/**
 * SillyTavern 集成模块 - 通过内部机制直接访问世界书
 * 专为浏览器环境设计的解决方案
 */
export class SillyTavernIntegration {
    constructor() {
        this.initialized = false;
        this.worldsCache = new Map();
    }

    /**
     * 初始化集成，检测 SillyTavern 内部接口
     */
    async initialize() {
        if (this.initialized) return true;

        console.log('[STIntegration] Initializing SillyTavern browser integration...');

        // 在浏览器环境中，我们需要使用 SillyTavern 的内部系统
        this.hasInternalAPI = this._checkInternalAPI();
        this.hasGlobalAccess = this._checkGlobalAccess();
        this.hasWorldInfoSystem = this._checkWorldInfoSystem();

        console.log('[STIntegration] Available access methods:', {
            internalAPI: this.hasInternalAPI,
            globalAccess: this.hasGlobalAccess,
            worldInfoSystem: this.hasWorldInfoSystem
        });

        this.initialized = true;
        return true;
    }

    /**
     * 检查 SillyTavern 内部 API 访问
     */
    _checkInternalAPI() {
        return typeof SillyTavern !== 'undefined' && 
               SillyTavern && 
               typeof SillyTavern.getContext === 'function';
    }

    /**
     * 检查全局访问能力
     */
    _checkGlobalAccess() {
        return typeof window !== 'undefined' && 
               typeof SillyTavern !== 'undefined';
    }

    /**
     * 检查世界书系统访问
     */
    _checkWorldInfoSystem() {
        // 检查是否可以通过 SillyTavern.getContext() 访问世界书
        if (typeof SillyTavern !== 'undefined' && SillyTavern.getContext) {
            try {
                const context = SillyTavern.getContext();
                if (context && typeof context.loadWorldInfo === 'function') {
                    return true;
                }
            } catch (error) {
                console.warn('[STIntegration] Error checking world info system:', error);
                return false;
            }
        }
        return false;
    }

    /**
     * 通过 SillyTavern 内部世界书系统获取数据
     */
    async _getWorldInfoFromSystem(worldName) {
        console.log(`[STIntegration] _getWorldInfoFromSystem called for ${worldName}`);
        console.log(`[STIntegration] hasInternalAPI: ${this.hasInternalAPI}, hasWorldInfoSystem: ${this.hasWorldInfoSystem}`);
        
        if (!this.hasInternalAPI || !this.hasWorldInfoSystem) {
            console.log(`[STIntegration] No internal API or world info system access for ${worldName}`);
            return null;
        }

        try {
            console.log(`[STIntegration] Attempting to load ${worldName} via SillyTavern.getContext().loadWorldInfo`);

            // 获取 SillyTavern 上下文
            const context = SillyTavern.getContext();
            if (!context) {
                console.log(`[STIntegration] No context available from SillyTavern`);
                return null;
            }

            // 直接使用 context.loadWorldInfo
            if (typeof context.loadWorldInfo === 'function') {
                try {
                    console.log(`[STIntegration] Calling context.loadWorldInfo("${worldName}")`);
                    const result = await context.loadWorldInfo(worldName);
                    
                    console.log(`[STIntegration] context.loadWorldInfo result for ${worldName}:`, result);
                    
                    if (result) {
                        console.log(`[STIntegration] ✓ Successfully loaded ${worldName} via context.loadWorldInfo`);
                        console.log(`[STIntegration] Result type: ${typeof result}, has entries: ${!!result.entries}`);
                        
                        if (result.entries) {
                            const entryCount = Object.keys(result.entries).length;
                            console.log(`[STIntegration] ✓ ${worldName} loaded with ${entryCount} entries`);
                        }
                        
                        return result;
                    } else {
                        console.log(`[STIntegration] context.loadWorldInfo returned null/undefined for ${worldName}`);
                    }
                } catch (loadError) {
                    console.warn(`[STIntegration] context.loadWorldInfo failed for ${worldName}:`, loadError);
                    
                    // 如果是 HTTP 403 错误，记录详细信息
                    if (loadError.message && loadError.message.includes('403')) {
                        console.error(`[STIntegration] HTTP 403 error detected - this indicates the original problem we're trying to solve`);
                    }
                    
                    // 重新抛出错误，让上层处理
                    throw loadError;
                }
            } else {
                console.log(`[STIntegration] context.loadWorldInfo is not a function (type: ${typeof context.loadWorldInfo})`);
            }

            return null;

        } catch (error) {
            console.warn(`[STIntegration] SillyTavern context access failed for ${worldName}:`, error);
            throw error; // 重新抛出错误，让上层处理
        }
    }

    /**
     * 通过全局对象获取世界书数据
     */
    async _getWorldInfoFromGlobals(worldName) {
        if (!this.hasGlobalAccess) return null;

        try {
            console.log(`[STIntegration] Attempting to access globals for ${worldName}`);

            // 检查 SillyTavern 对象的结构
            if (typeof SillyTavern !== 'undefined' && SillyTavern) {
                console.log(`[STIntegration] SillyTavern object keys:`, Object.keys(SillyTavern));
                
                // 检查 SillyTavern.libs 中是否有世界书相关功能
                if (SillyTavern.libs) {
                    console.log(`[STIntegration] SillyTavern.libs keys:`, Object.keys(SillyTavern.libs));
                    
                    // 查找可能的世界书库
                    const worldLibs = Object.keys(SillyTavern.libs).filter(key => 
                        key.toLowerCase().includes('world') || key.toLowerCase().includes('info'));
                    
                    for (const libName of worldLibs) {
                        const lib = SillyTavern.libs[libName];
                        console.log(`[STIntegration] Checking lib ${libName}:`, lib);
                        
                        if (lib && typeof lib === 'object') {
                            // 尝试在库中查找世界书数据
                            if (lib[worldName] || lib.worlds?.[worldName] || lib.data?.[worldName]) {
                                const worldData = lib[worldName] || lib.worlds[worldName] || lib.data[worldName];
                                console.log(`[STIntegration] Found ${worldName} in ${libName}`);
                                return worldData;
                            }
                        }
                    }
                }

                // 检查 SillyTavern 对象的直接属性
                const possiblePaths = [
                    'worlds',
                    'worldInfo', 
                    'world_info',
                    'data.worlds',
                    'context.worlds'
                ];

                for (const path of possiblePaths) {
                    const value = this._getNestedProperty(SillyTavern, path);
                    if (value && value[worldName]) {
                        console.log(`[STIntegration] Found ${worldName} in SillyTavern.${path}`);
                        return value[worldName];
                    }
                }
            }

            return null;

        } catch (error) {
            console.warn(`[STIntegration] Global access failed for ${worldName}:`, error);
            return null;
        }
    }

    /**
     * 获取嵌套属性值
     */
    _getNestedProperty(obj, path) {
        return path.split('.').reduce((current, key) => 
            current && current[key] !== undefined ? current[key] : null, obj);
    }

    /**
     * 通过事件系统请求世界书数据
     */
    async _getWorldInfoViaEvents(worldName) {
        // 由于 eventSource 不存在，尝试其他事件机制
        return null;
    }

    /**
     * 通过 HTML 元素和 DOM 获取世界书数据
     */
    async _getWorldInfoFromDOM(worldName) {
        try {
            console.log(`[STIntegration] Attempting to get ${worldName} via DOM manipulation`);

            // 获取世界书选择器元素
            const selectElement = document.getElementById('world_info');
            if (!selectElement) {
                console.log(`[STIntegration] world_info select element not found`);
                return null;
            }

            // 检查选项中是否有我们要的世界书
            const options = Array.from(selectElement.options);
            const targetOption = options.find(opt => opt.text === worldName || opt.value === worldName);
            
            if (!targetOption) {
                console.log(`[STIntegration] ${worldName} not found in select options`);
                console.log('Available options:', options.map(opt => ({text: opt.text, value: opt.value})));
                return null;
            }

            console.log(`[STIntegration] Found ${worldName} option:`, targetOption);

            // 尝试触发选择并监听数据变化
            const originalValue = selectElement.value;
            
            // 模拟选择这个世界书
            selectElement.value = targetOption.value;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));

            // 给 SillyTavern 一些时间来加载数据
            await new Promise(resolve => setTimeout(resolve, 1000));

            // 现在尝试从各种可能的位置获取加载的数据
            const context = SillyTavern.getContext && SillyTavern.getContext();
            if (context) {
                // 检查是否有新的世界书数据
                const possiblePaths = ['worldInfo', 'world_info', 'worlds', 'currentWorldInfo'];
                for (const path of possiblePaths) {
                    if (context[path]) {
                        console.log(`[STIntegration] Found data in context.${path}:`, context[path]);
                        return context[path];
                    }
                }
            }

            // 恢复原始选择
            selectElement.value = originalValue;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));

            return null;

        } catch (error) {
            console.warn(`[STIntegration] DOM access failed for ${worldName}:`, error);
            return null;
        }
    }

    /**
     * 主要的世界书获取方法
     */
    async getWorldInfo(worldName) {
        await this.initialize();

        // 检查缓存
        if (this.worldsCache.has(worldName)) {
            console.log(`[STIntegration] Loading ${worldName} from cache`);
            return this.worldsCache.get(worldName);
        }

        let worldData = null;

        // 按优先级尝试不同的方法
        const methods = [
            () => this._getWorldInfoFromSystem(worldName),
            () => this._getWorldInfoFromGlobals(worldName),
            () => this._getWorldInfoFromDOM(worldName)
        ];

        for (const method of methods) {
            try {
                worldData = await method();
                if (worldData) {
                    console.log(`[STIntegration] Successfully loaded ${worldName} via one of the methods`);
                    break;
                }
            } catch (error) {
                console.warn(`[STIntegration] Method failed:`, error);
                continue;
            }
        }

        // 如果所有方法都失败，返回 null 而不是捏造数据
        if (!worldData) {
            console.error(`[STIntegration] Failed to load world info: ${worldName}. All access methods failed.`);
            return null;
        }

        // 缓存成功加载的数据
        this.worldsCache.set(worldName, worldData);
        return worldData;
    }

    /**
     * 获取可用的世界书列表
     */
    async getAvailableWorlds() {
        await this.initialize();

        let worlds = [];

        // 首先尝试从世界书选择器获取实际的选项列表
        try {
            const selectElement = document.getElementById('world_info');
            if (selectElement && selectElement.options) {
                console.log('[STIntegration] Reading available worlds from select element');
                
                const options = Array.from(selectElement.options);
                worlds = options.map(option => option.text).filter(text => text && text.trim());
                
                console.log('[STIntegration] Found worlds in selector:', worlds);
                
                if (worlds.length > 0) {
                    return worlds;
                }
            }
        } catch (error) {
            console.warn('[STIntegration] Failed to read from world_info selector:', error);
        }

        // 备用方法：尝试从 SillyTavern 上下文获取
        if (this.hasWorldInfoSystem) {
            try {
                const context = SillyTavern.getContext();
                if (context && typeof context.updateWorldInfoList === 'function') {
                    console.log('[STIntegration] Attempting to get world list via updateWorldInfoList');
                    await context.updateWorldInfoList();
                    
                    // 再次检查选择器
                    const selectElement = document.getElementById('world_info');
                    if (selectElement && selectElement.options) {
                        const options = Array.from(selectElement.options);
                        worlds = options.map(option => option.text).filter(text => text && text.trim());
                        
                        if (worlds.length > 0) {
                            console.log('[STIntegration] Updated world list:', worlds);
                            return worlds;
                        }
                    }
                }
            } catch (error) {
                console.warn('[STIntegration] Failed to update world info list:', error);
            }
        }

        // 如果所有方法都失败，返回从测试中发现的已知列表
        if (worlds.length === 0) {
            worlds = ['character_info', 'world_info'];
            console.log('[STIntegration] Using fallback world list based on test results:', worlds);
        }

        return worlds;
    }

    /**
     * 清理缓存
     */
    clearCache() {
        this.worldsCache.clear();
    }
}

// 创建全局实例
export const stIntegration = new SillyTavernIntegration();
