import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.jsx';

// ======================================================
// 关键引入:
// CacheProvider 用于向其子组件提供自定义的 emotion 缓存。
// createCache 用于创建这个自定义缓存实例。
// ======================================================
import { CacheProvider } from '@emotion/react';
import createCache from '@emotion/cache';


// ---------------------------------
// 阶段一: 定义 Web Component
// ---------------------------------
class GoliathAppRoot extends HTMLElement {
    constructor() {
        super();
        this.reactRoot = null;
    }

    connectedCallback() {
        const shadowRoot = this.attachShadow({ mode: 'open' });
        const mountPoint = document.createElement('div');
        mountPoint.id = 'react-app-mount-point';
        shadowRoot.appendChild(mountPoint);

        // ======================================================
        // 关键修复: 创建并配置 Emotion 缓存
        // ======================================================
        const cache = createCache({
            // `key` 是一个前缀，emotion 会用它来生成 class 名称。
            key: 'css', 
            // `container` 是最关键的设置。
            // 我们告诉 emotion 把所有生成的 <style> 标签都插入到这个容器里，
            // 而这个容器就是我们的 shadowRoot！
            container: shadowRoot,
        });

        // 创建并渲染 React 应用
        this.reactRoot = createRoot(mountPoint);
        this.reactRoot.render(
            <React.StrictMode>
                {/* 
                  使用 CacheProvider 包裹我们的应用，
                  并将我们创建的自定义缓存通过 value prop 传递下去。
                */}
                <CacheProvider value={cache}>
                    <App />
                </CacheProvider>
            </React.StrictMode>
        );
        console.log('[Goliath] React App mounted into Shadow DOM with custom style cache.');
    }

    disconnectedCallback() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            console.log('[Goliath] React App unmounted.');
        }
    }
}

// ---------------------------------
// 插件注册函数 (此部分无需修改)
// ---------------------------------
export function registerPlugin(context) {
    console.log('[Goliath] Stage 1: Defining custom element <goliath-app-root>...');
    customElements.define('goliath-app-root', GoliathAppRoot);

    const hookManager = context.get('hookManager');
    if (!hookManager) { return; }

    hookManager.addImplementation('host.ready', () => {
        console.log('[Goliath] Stage 2: host.ready received, registering command handlers...');
        const commandService = context.get('commandService');
        if (commandService) {
            commandService.registerHandler(
                'goliath.show.about',
                () => {
                    hookManager.trigger('ui.show.aboutDialog');
                }
            );
        }
    });
}