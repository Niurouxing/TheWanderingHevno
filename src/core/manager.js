// src/core/manager.js

/**
 * @file manager.js
 * @description 插件的核心管理器和API抽象层。
 */

// I. 导入SillyTavern的核心功能
import {
    eventSource,
    event_types,
    saveSettingsDebounced,
    saveReply,
    saveChatConditional,
    activateSendButtons,
    addOneMessage,
    deleteLastMessage,
    generateRaw,
    reloadCurrentChat,
    sendSystemMessage,
    substituteParams,
} from '/script.js';
import { getTokenCountAsync } from '/scripts/tokenizers.js';
import { getContext, extension_settings, renderExtensionTemplateAsync } from '/scripts/extensions.js';
import { Popup, POPUP_TYPE, callGenericPopup } from '/scripts/popup.js';

// 【修改】导入正确的、高层的API和可写变量
import {
    getWorldInfoPrompt,
    selected_world_info,
    loadWorldInfo,
    world_names,
    world_info, // 添加这个导入来访问世界书数据
} from '/scripts/world-info.js';

import { defaultSettings } from '../data/pluginSetting.js';

// II. 定义和导出管理器

/**
 * @namespace APP
 * @description 应用管理器 (APP)
 */
export const APP = {
    getContext,
    eventSource,
    event_types,
    saveReply,
    unblockGeneration: activateSendButtons,
    generateRaw,
    addOneMessage,
    sendSystemMessage,
    deleteLastMessage,
    reloadCurrentChat,
    saveChatConditional,
    renderExtensionTemplateAsync,
    substituteParams,
    getTokenCountAsync,
};

/**
 * @namespace USER
 * @description 用户数据管理器 (USER)
 */
export const USER = {
    settings: new Proxy({}, {
        get(_, property) {
            const settings = extension_settings.Hevno_settings;
            if (settings && property in settings) {
                return settings[property];
            }
            return defaultSettings[property];
        },
        set(_, property, value) {
            if (!extension_settings.Hevno_settings) {
                extension_settings.Hevno_settings = {};
            }
            extension_settings.Hevno_settings[property] = value;
            saveSettingsDebounced();
            return true;
        },
    }),
    saveSettings: saveSettingsDebounced,
};

/**
 * @namespace EDITOR
 * @description 编辑器/UI管理器 (EDITOR)
 */
export const EDITOR = {
    Popup,
    POPUP_TYPE,
    callGenericPopup,
};

/**
 * @namespace SYSTEM
 * @description 系统工具管理器 (SYSTEM)
 */
export const SYSTEM = {
    getTemplate: (name) => {
        return APP.renderExtensionTemplateAsync('third-party/Hevno/assets/templates', name);
    },

    /**
     * 【最终版】封装 SillyTavern 的顶层 World Info 获取函数。
     * @param {Array<string>} chat - 聊天消息文本数组
     * @param {number} maxContext - 最大上下文大小
     * @param {boolean} isDryRun - 是否为演练模式
     * @param {object} globalScanData - 角色、场景等附加扫描数据
     * @returns {Promise<object>} 返回一个包含 .worldInfoString 的对象
     */
    getWorldInfoPrompt: getWorldInfoPrompt,

    /**
     * 获取当前全局选择的世界书列表。
     * @returns {Array<string>}
     */
    getSelectedWorldInfo: () => [...selected_world_info],

    /**
     * 临时设置SillyTavern全局选择的世界书列表。
     * @param {Array<string>} worlds - 世界书文件名列表。
     */
    setSelectedWorldInfo: (worlds) => {
        selected_world_info.length = 0;
        selected_world_info.push(...worlds);
    },

    /**
     * 【新增】直接暴露SillyTavern的WI文件加载函数。
     * @param {string} worldName - 要加载的世界书文件名。
     * @returns {Promise<object|null>} 加载的数据或null。
     */
    loadWorldInfo: loadWorldInfo,

    /**
     * 【新增】清理世界书缓存和状态
     */
    clearWorldInfoCache: () => {
        try {
            // 清理world_info中的所有条目
            if (world_info && typeof world_info === 'object') {
                Object.keys(world_info).forEach(key => {
                    delete world_info[key];
                });
            }
            console.log('[SYSTEM] World info cache cleared');
        } catch (error) {
            console.warn('[SYSTEM] Failed to clear world info cache:', error);
        }
    },

    /**
     * 【新增】卸载所有已加载的世界书（但保留选择列表）
     */
    unloadAllWorldInfo: async () => {
        try {
            // 【修复】只清理世界书数据缓存，不清理选择列表
            // 这样loadWorldInfo可以重新加载，但selected_world_info保持正确状态
            if (world_info && typeof world_info === 'object') {
                Object.keys(world_info).forEach(key => {
                    delete world_info[key];
                });
            }
            
            console.log('[SYSTEM] World info data cleared (keeping selection)');
        } catch (error) {
            console.warn('[SYSTEM] Failed to unload world info:', error);
        }
    },


    /**
     * 【新增】获取所有已知的世界书文件名。
     * @returns {Array<string>}
     */
    getWorldNames: () => [...world_names],


    /**
     * 【新增】临时设置所有已知的世界书文件名。
     * @param {Array<string>} newWorldNames - 新的世界书文件名列表。
     */
    setWorldNames: (newWorldNames) => {
        world_names.length = 0; // Clear the array
        Array.prototype.push.apply(world_names, newWorldNames); // Mutate it
    },

    /**
     * 获取角色数据
     * @returns {Array}
     */
    getCharacters: () => getContext()?.characters || [],

    /**
     * 获取当前角色ID
     * @returns {number}
     */
    getCurrentCharacterId: () => getContext()?.characterId || -1,

    /**
     * 获取聊天元数据
     * @returns {object}
     */
    getChatMetadata: () => getContext()?.chat_metadata || {},

    /**
     * 设置聊天元数据
     * @param {string} key
     * @param {any} value
     */
    setChatMetadata: (key, value) => {
        const context = getContext();
        if (context?.chat_metadata) {
            context.chat_metadata[key] = value;
        }
    },

    /**
     * 获取power_user对象
     * @returns {object}
     */
    getPowerUser: () => getContext()?.power_user || {},

    /**
     * METADATA_KEY常量
     */
    METADATA_KEY: 'world_info',

    /**
     * 获取世界书数据对象
     * @returns {object}
     */
    getWorldInfoData: () => world_info,
};