import React from 'react';
import { createRoot } from 'react-dom/client';


// 导入应用的根组件
import App from './App.jsx';

// 全局标志位，用于防止在开发模式的热重载(HMR)中重复执行初始化逻辑
if (typeof window.hevnoGoliathInitialized === 'undefined') {
  window.hevnoGoliathInitialized = false;
}

/**
 * 这是 Goliath React 应用的 Web Component 封装器。
 * 它的职责是作为平台和 React 应用之间的桥梁。
 */
class GoliathAppRoot extends HTMLElement {
    constructor() {
        super();
        this.reactRoot = null;
    }

    connectedCallback() {
        // 关键变更: 不再调用 this.attachShadow()
        // 我们将直接在这个宿主元素 (this) 上渲染 React 应用。
        
        // 确保挂载点只被创建一次
        if (!this.reactRoot) {
            this.reactRoot = createRoot(this); // 直接使用 this 作为容器
            
            // 直接渲染 App，无需任何 Provider，因为 App 内部会处理
            this.reactRoot.render(
                <React.StrictMode>
                    <App />
                </React.StrictMode>
            );
            console.log('[Goliath] React App mounted directly onto the host element (No Shadow DOM).');
        }
    }


    /**
     * 当此元素从 DOM 中移除时调用。
     * 在这里清理 React 应用以防止内存泄漏。
     */
    disconnectedCallback() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            this.reactRoot = null;
            console.log('[Goliath] React App unmounted.');
        }
    }
}

/**
 * Hevno 插件系统的入口函数。
 * 由前端加载器在加载此插件时调用。
 * @param {import('../../../frontend/ServiceContainer').ServiceContainer} context - 平台服务容器
 */
export function registerPlugin(context) {
    // 检查标志位，防止重复注册
    if (window.hevnoGoliathInitialized) {
        console.warn('[Goliath] Attempted to re-register. Aborting.');
        return;
    }
    window.hevnoGoliathInitialized = true;

    // --- 阶段一: 同步的、无依赖的初始化 ---
    console.log('[Goliath] Stage 1: Initializing plugin...');

    // 使用 customElements.get() 检查，这是定义 Web Component 的最安全方式
    if (!customElements.get('goliath-app-root')) {
        customElements.define('goliath-app-root', GoliathAppRoot);
        console.log('[Goliath] Custom element <goliath-app-root> defined.');
    }

    const hookManager = context.get('hookManager');
    if (!hookManager) { 
        console.error('[Goliath] Critical: HookManager not found.');
        return; 
    }

    // --- 阶段二: 注册异步的、依赖应用服务的逻辑 ---
    // 我们注册一个对 `host.ready` 钩子的监听。
    // 这个钩子由 `core_layout` 插件在所有应用层服务准备好后触发。
    hookManager.addImplementation('host.ready', () => {
        console.log('[Goliath] Stage 2: host.ready received, registering command handlers...');

        // 此刻获取应用层服务是安全的
        const commandService = context.get('commandService');
        if (commandService) {
            commandService.registerHandler(
                'goliath.show.about', // 这个 ID 来自 manifest.json
                () => {
                    // 不直接操作 UI，而是触发一个语义化的钩子
                    // React 组件会监听这个钩子并更新自己的状态来显示对话框
                    hookManager.trigger('ui.show.aboutDialog');
                }
            );
        }
    });
}