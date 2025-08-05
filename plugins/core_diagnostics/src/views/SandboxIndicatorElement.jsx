import React from 'react';
import { createRoot } from 'react-dom/client';
import { SandboxIndicator } from '../components/SandboxIndicator.jsx';

export class SandboxIndicatorElement extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
    }
    
    connectedCallback() {
        this.reactRoot = createRoot(this.shadowRoot);
        this.reactRoot.render(
            <React.StrictMode>
                <SandboxIndicator />
            </React.StrictMode>
        );
    }

    disconnectedCallback() {
        if (this.reactRoot) this.reactRoot.unmount();
    }
}