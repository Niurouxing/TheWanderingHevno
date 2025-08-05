// plugins/core_statusbar_item/src/main.jsx

import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConnectionStatus } from './ConnectionStatus.jsx';

// 【修改】极大地简化了Web Component封装器
class ReactWebComponent extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
    }

    // 【删除】不再需要 _context, set context(), get context()
    
    connectedCallback() {
        // 当元素连接到 DOM 时，创建 React root 并渲染组件
        this.reactRoot = createRoot(this.shadowRoot);
        this.render();
    }

    disconnectedCallback() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            this.reactRoot = null;
        }
    }

    render() {
        if (this.reactRoot) {
            // 【修改】渲染逻辑变得极其简单。
            // 不再需要检查 context 是否存在，也不再需要传递任何 props。
            // ConnectionStatus 组件会自己处理依赖。
            this.reactRoot.render(
                <React.StrictMode>
                    <ConnectionStatus />
                </React.StrictMode>
            );
        }
    }
}

export function registerPlugin(context) {
    if (!customElements.get('connection-status-element')) {
        customElements.define('connection-status-element', ReactWebComponent);
        console.log('[Statusbar React] DEFINED custom element "connection-status-element"');
    }
}