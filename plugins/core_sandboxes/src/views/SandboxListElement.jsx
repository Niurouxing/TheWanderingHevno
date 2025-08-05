// plugins/core_sandboxes/src/views/SandboxListElement.jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import { SandboxList } from '../components/SandboxList.jsx';

// 遵循黄金规则五：封装 UI 为 Web Components
export class SandboxListElement extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
    }

    connectedCallback() {
        // 将样式注入 Shadow DOM
        const style = document.createElement('style');
        style.textContent = `
            :host {
                display: block;
                height: 100%;
            }
        `;
        this.shadowRoot.appendChild(style);

        const mountPoint = document.createElement('div');
        this.shadowRoot.appendChild(mountPoint);

        this.reactRoot = createRoot(mountPoint);
        this.reactRoot.render(
            <React.StrictMode>
                <SandboxList />
            </React.StrictMode>
        );
    }

    disconnectedCallback() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
        }
    }
}