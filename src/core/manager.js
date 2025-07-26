// src/core/manager.js (附有详细注释文档)

/**
 * @file manager.js
 * @description 插件的核心管理器和API抽象层。
 * @version 1.1.0
 *
 * @see README.md - 插件的整体架构设计。
 *
 * @summary
 * 这个文件是插件与SillyTavern进行交互的唯一桥梁。它将SillyTavern复杂、有时甚至是全局的API
 * 封装成一组逻辑清晰、易于管理的单例对象（APP, USER, EDITOR, SYSTEM）。
 *
 * 【新开发者必读】
 * 任何与SillyTavern的直接交互（如调用函数、获取数据）都应该首先在这里进行封装。
 * 插件的其他部分（如index.js）应优先调用这里的管理器，而不是直接触碰SillyTavern的API。
 * 这种设计模式（称为“外观模式”或“适配器模式”）有以下好处：
 * 1.  **解耦**: 插件的业务逻辑与SillyTavern的实现细节分离。
 * 2.  **可维护性**: 如果SillyTavern未来更新了API，我们只需要修改这个文件，而不用改动整个插件。
 * 3.  **清晰性**: 提供了清晰的API边界，新开发者能快速了解插件可用的所有SillyTavern功能。
 */

// ===================================================================================
// I. 导入SillyTavern的核心功能
// ===================================================================================
// 注意: 导入路径是相对于SillyTavern的 /public/ 目录的。

// 从 /script.js 导入SillyTavern的核心功能函数。
// 这些函数大多是经过 `export` 关键字明确导出的“公共API”。
import {
    // 事件系统
    eventSource,
    event_types,
    // 设置与持久化
    saveSettingsDebounced,
    // 核心消息处理 (!!!)
    saveReply,
    saveChatConditional,
    activateSendButtons,
    // 其他常用工具
    addOneMessage,
    deleteLastMessage,
    generateRaw,
    reloadCurrentChat,
    sendSystemMessage,
    substituteParams,
    
} from '/script.js';

import {getTokenCountAsync} from '/scripts/tokenizers.js'; // 异步计算token数量的函数

// 从 /scripts/extensions.js 导入专门为插件提供的功能。
import { getContext, extension_settings, renderExtensionTemplateAsync } from '/scripts/extensions.js';
// 从 /scripts/popup.js 导入UI组件。
import { Popup, POPUP_TYPE, callGenericPopup } from '/scripts/popup.js';

// 导入插件自身的默认设置，作为回退方案。
import { defaultSettings } from '../data/pluginSetting.js';


// ===================================================================================
// II. 定义和导出管理器
// ===================================================================================

/**
 * @namespace APP
 * @description 应用管理器 (APP): 封装与SillyTavern应用本身交互的核心API。
 *              这是最常用的管理器，提供了对SillyTavern状态和核心流程的访问。
 */
export const APP = {
    // -----------------------------------------------------------------------------
    // 核心上下文与数据 API
    // -----------------------------------------------------------------------------

    /**
     * @function getContext
     * @description (!!!) 获取SillyTavern的全局上下文对象。这是访问所有运行时数据的入口。
     * @returns {object} 上下文对象，包含 chat, characters, settings, eventSource 等。
     * @see https://docs.sillytavern.app/extensions/api/context/
     */
    getContext,

    // -----------------------------------------------------------------------------
    // 事件系统 API
    // -----------------------------------------------------------------------------

    /**
     * @property {EventEmitter} eventSource
     * @description SillyTavern的事件发射器，用于监听应用内的各种事件。
     * @example APP.eventSource.on(APP.event_types.MESSAGE_RECEIVED, (messageId) => { ... });
     */
    eventSource,

    /**
     * @property {object} event_types
     * @description 一个包含所有可用事件名称的枚举对象。
     * @see https://docs.sillytavern.app/extensions/api/events/
     */
    event_types,

    // -----------------------------------------------------------------------------
    // 消息处理与生成流程控制 API
    // -----------------------------------------------------------------------------

    /**
     * @function saveReply
     * @description (!!!) 【推荐】将一个字符串作为AI回复注入SillyTavern的完整消息处理流程。
     *              这是实现“喂回”机制的核心，比 addOneMessage 更健壮。
     * @param {object} options - 包含回复信息的对象。
     * @example await APP.saveReply({ type: 'normal', getMessage: '你好！' });
     */
    saveReply,

    /**
     * @function activateSendButtons
     * @description (!!!) 【关键】解锁UI，重新启用发送按钮。在拦截并中止生成后，必须在finally块中调用此函数。
     *              这是 unblockGeneration 的安全、公共的替代品。
     */
    unblockGeneration: activateSendButtons,

    /**
     * @function generateRaw
     * @description 【未来可用】在后台静默发起一次LLM调用，不影响当前聊天界面。
     *              对于需要LLM进行数据处理的复杂插件（如摘要、翻译）非常有用。
     * @param {string} prompt - 要发送给LLM的提示。
     * @returns {Promise<string>} LLM生成的文本。
     */
    generateRaw,

    // -----------------------------------------------------------------------------
    // 聊天记录操作 API
    // -----------------------------------------------------------------------------

    /**
     * @function addOneMessage
     * @description 【未来可用】将一个标准格式的消息对象直接渲染到聊天界面。
     *              主要用于添加非AI生成的、系统性的消息。对于AI回复，应优先使用 saveReply。
     * @param {object} messageObject - 符合SillyTavern格式的消息对象。
     */
    addOneMessage,

    /**
     * @function sendSystemMessage
     * @description 【未来可用】一个更高级的函数，用于方便地发送格式化的系统消息。
     * @param {string} type - 系统消息类型, e.g., 'generic', 'comment'。
     * @param {string} text - 消息内容。
     */
    sendSystemMessage,

    /**
     * @function deleteLastMessage
     * @description 【未来可用】删除聊天记录中的最后一条消息。
     */
    deleteLastMessage,

    /**
     * @function reloadCurrentChat
     * @description 【未来可用】强制重新加载和渲染整个聊天界面。
     *              在你对聊天状态做了大量底层修改后，可以使用此函数来确保UI同步。
     */
    reloadCurrentChat,

    // -----------------------------------------------------------------------------
    // 持久化 API
    // -----------------------------------------------------------------------------

    /**
     * @function saveChatConditional
     * @description (!!!) 保存当前的聊天记录到文件。
     */
    saveChatConditional,

    // -----------------------------------------------------------------------------
    // 模板与工具 API
    // -----------------------------------------------------------------------------

    /**
     * @function renderExtensionTemplateAsync
     * @description 【UI】异步加载并渲染插件的HTML模板文件。
     */
    renderExtensionTemplateAsync,

    /**
     * @function substituteParams
     * @description 【未来可用】替换字符串中的宏，如 {{user}}, {{char}}。
     */
    substituteParams,

    /**
     * @function getTokenCountAsync
     * @description 【未来可用】异步计算给定字符串的token数量。对于需要管理上下文长度的插件至关重要。
     */
    getTokenCountAsync,
};


/**
 * @namespace USER
 * @description 用户数据管理器 (USER): 专门处理本插件的设置，提供优雅的读取和保存接口。
 */
export const USER = {
    /**
     * @property {object} settings
     * @description 一个Proxy对象，用于访问插件设置。
     *              它会自动处理从SillyTavern的`extension_settings`中读取数据，
     *              并在找不到值时回退到`defaultSettings`。
     * @example const isEnabled = USER.settings.isEnabled;
     * @example USER.settings.demoString = "New value"; // 这会自动触发保存
     */
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

    /**
     * @function saveSettings
     * @description 手动触发一次设置保存（带防抖）。通常不需要手动调用，因为`USER.settings`的set操作会自动保存。
     */
    saveSettings: saveSettingsDebounced,
};


/**
 * @namespace EDITOR
 * @description 编辑器/UI管理器 (EDITOR): 封装与SillyTavern UI组件的交互，如弹窗。
 */
export const EDITOR = {
    Popup,
    POPUP_TYPE,
    callGenericPopup,
};


/**
 * @namespace SYSTEM
 * @description 系统工具管理器 (SYSTEM): 封装插件的系统级操作，主要是资源加载。
 */
export const SYSTEM = {
    /**
     * @function getTemplate
     * @description 加载位于插件 `assets/templates` 目录下的HTML模板。
     * @param {string} name - HTML文件名（不含.html后缀）。
     * @returns {Promise<string>} HTML内容的字符串。
     * @example const settingsHtml = await SYSTEM.getTemplate('settings');
     */
    getTemplate: (name) => {
        // 注意：这里的路径是相对于 /public/extensions/ 目录的。
        // 如果你的插件文件夹是 Hevno，并且位于 third-party 子目录，路径就是 'third-party/Hevno/...'
        return APP.renderExtensionTemplateAsync('third-party/Hevno/assets/templates', name);
    },
};