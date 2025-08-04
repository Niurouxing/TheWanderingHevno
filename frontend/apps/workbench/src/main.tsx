// frontend/apps/workbench/src/main.tsx
import '@hevno/kernel/main';


import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

window.Hevno.services.hooks.addImplementation('plugins:ready', () => {
    ReactDOM.createRoot(document.getElementById('hevno-root')!).render(
        <React.StrictMode>
            <App />
        </React.StrictMode>
    );
});