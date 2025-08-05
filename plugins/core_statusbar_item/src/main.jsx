// plugins/core_statusbar_item/src/main.jsx

import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConnectionStatus } from './ConnectionStatus.jsx';

class ReactWebComponent extends HTMLElement {
    // ... constructor, set/get context, connected/disconnectedCallback 不变 ...
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
        this._context = null;
    }

    set context(value) {
        this._context = value;
        // 【重要】我们在这里只保存 context，让 connectedCallback 统一处理渲染
        // 这可以避免在元素添加到 DOM 前就尝试渲染
        if (this.reactRoot) {
            this.render();
        }
    }

    get context() {
        return this._context;
    }

    connectedCallback() {
        this.reactRoot = createRoot(this.shadowRoot);
        // 当元素连接到 DOM 时，此时 context 可能已经被设置了，也可能没有
        // 无论如何，都尝试渲染一次
        this.render();
    }

    disconnectedCallback() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            this.reactRoot = null;
        }
    }

    // 【关键修复】重写 render 方法
    render() {
        // 只有在元素已连接到 DOM (reactRoot存在) 时才渲染
        if (this.reactRoot) {
            // 我们不再依赖 prop 传递，而是直接将 context 传递给组件。
            // 这是一个更可靠的方式，可以绕过任何潜在的 prop 传递问题。
            const componentToRender = this._context 
                ? <ConnectionStatus context={this._context} />
                : <p>Loading...</p>; // 提供一个加载状态，以防 context 延迟到达

            this.reactRoot.render(
                <React.StrictMode>
                    {componentToRender}
                </React.StrictMode>
            );
        }
    }
}

// ... registerPlugin 函数保持不变 ...
export function registerPlugin(context) {
    if (!customElements.get('connection-status-element')) {
        customElements.define('connection-status-element', ReactWebComponent);
        console.log('[Statusbar React] DEFINED custom element "connection-status-element"');
    }
}