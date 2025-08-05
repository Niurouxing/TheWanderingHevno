import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConnectionStatus } from '../components/ConnectionStatus.jsx';

export class ConnectionStatusElement extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
    }
    
    connectedCallback() {
        this.reactRoot = createRoot(this.shadowRoot);
        this.reactRoot.render(
            <React.StrictMode>
                <ConnectionStatus />
            </React.StrictMode>
        );
    }

    disconnectedCallback() {
        if (this.reactRoot) this.reactRoot.unmount();
    }
}