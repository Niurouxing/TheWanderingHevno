import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.jsx'; // 导入我们的根 React 组件

// ---------------------------------
// 阶段一: 定义 Web Component
// ---------------------------------
class GoliathAppRoot extends HTMLElement {
    constructor() {
        super();
        this.reactRoot = null;
    }

    connectedCallback() {
        // 使用 Shadow DOM 进行样式隔离，这是最佳实践
        const shadowRoot = this.attachShadow({ mode: 'open' });

        // 在 Shadow DOM 中创建一个挂载点，MUI 的模态框等会需要这个
        const mountPoint = document.createElement('div');
        mountPoint.id = 'react-app-mount-point';
        shadowRoot.appendChild(mountPoint);

        // 创建并渲染 React 应用
        this.reactRoot = createRoot(mountPoint);
        this.reactRoot.render(
            <React.StrictMode>
                <App />
            </React.StrictMode>
        );
        console.log('[Goliath] React App mounted into Shadow DOM.');
    }

    disconnectedCallback() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            console.log('[Goliath] React App unmounted.');
        }
    }
}

// ---------------------------------
// 插件注册函数
// ---------------------------------
export function registerPlugin(context) {
    // 阶段一: 在插件加载时立即执行的同步、无依赖任务
    console.log('[Goliath] Stage 1: Defining custom element <goliath-app-root>...');
    customElements.define('goliath-app-root', GoliathAppRoot);

    const hookManager = context.get('hookManager');
    if (!hookManager) { return; }

    // 阶段二: 注册 host.ready 监听器，用于执行依赖应用层服务的逻辑
    hookManager.addImplementation('host.ready', () => {
        console.log('[Goliath] Stage 2: host.ready received, registering command handlers...');

        // 此刻获取应用层服务是安全的
        const commandService = context.get('commandService');
        if (commandService) {
            commandService.registerHandler(
                'goliath.show.about',
                () => {
                    // 触发一个钩子，让 React 组件去响应并显示对话框
                    hookManager.trigger('ui.show.aboutDialog');
                }
            );
        }
    });
}