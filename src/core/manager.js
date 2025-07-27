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
    getSelectedWorldInfo: () => [...window.selected_world_info],

    /**
     * 临时设置SillyTavern全局选择的世界书列表。
     * @param {Array<string>} worlds - 世界书文件名列表。
     */
    setSelectedWorldInfo: (worlds) => {
        window.selected_world_info.length = 0;
        window.selected_world_info.push(...worlds);
    },

    /**
     * 【新增】直接暴露SillyTavern的WI文件加载函数。
     * @param {string} worldName - 要加载的世界书文件名。
     * @returns {Promise<object|null>} 加载的数据或null。
     */
    loadWorldInfo: loadWorldInfo,


    /**
     * 【新增】获取所有已知的世界书文件名。
     * @returns {Array<string>}
     */
    getWorldNames: () => [...window.world_names],


    /**
     * 【新增】临时设置所有已知的世界书文件名。
     * @param {Array<string>} newWorldNames - 新的世界书文件名列表。
     */
    setWorldNames: (newWorldNames) => {
        world_names.length = 0; // Clear the array
        Array.prototype.push.apply(world_names, newWorldNames); // Mutate it
    },
};