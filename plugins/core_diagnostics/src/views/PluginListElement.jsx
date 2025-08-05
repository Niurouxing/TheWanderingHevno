import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';

function PluginList() {
    const [plugins, setPlugins] = useState([]);
    const manifestProvider = window.Hevno.services.get('manifestProvider');

    useEffect(() => {
        if (manifestProvider) {
            const frontendPlugins = manifestProvider.getManifests()
                .filter(m => m.frontend)
                .sort((a,b) => a.id.localeCompare(b.id));
            setPlugins(frontendPlugins);
        }
    }, [manifestProvider]);

    const style = {
        listStyle: 'none',
        padding: 0,
        margin: 0,
        fontSize: '0.9em'
    };

    const itemStyle = {
        display: 'flex',
        justifyContent: 'space-between',
        padding: '2px 0',
    };

    return (
        <ul style={style}>
            {plugins.map(plugin => (
                <li key={plugin.id} style={itemStyle}>
                    <span>{plugin.name}</span>
                    <small style={{ opacity: 0.6 }}>v{plugin.version}</small>
                </li>
            ))}
        </ul>
    );
}


export class PluginListElement extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.reactRoot = null;
    }
    
    connectedCallback() {
        this.reactRoot = createRoot(this.shadowRoot);
        this.reactRoot.render(
            <React.StrictMode>
                <PluginList />
            </React.StrictMode>
        );
    }

    disconnectedCallback() {
        if (this.reactRoot) this.reactRoot.unmount();
    }
}