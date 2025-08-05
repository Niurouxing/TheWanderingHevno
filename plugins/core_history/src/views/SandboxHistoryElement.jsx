import React from 'react';
import { createRoot } from 'react-dom/client';
import { HistoryView } from '../components/HistoryView.jsx';

export class SandboxHistoryElement extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
    }
    
    connectedCallback() {
        const mountPoint = document.createElement('div');
        this.shadowRoot.appendChild(mountPoint);
        this.reactRoot = createRoot(mountPoint);
        this.reactRoot.render(
            <React.StrictMode>
                <HistoryView />
            </React.StrictMode>
        );
    }

    disconnectedCallback() {
        if (this.reactRoot) this.reactRoot.unmount();
    }
}