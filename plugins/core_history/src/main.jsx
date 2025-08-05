import { SandboxHistoryElement } from './views/SandboxHistoryElement.jsx';

export function registerPlugin(context) {
    console.log('[core_history] Stage 1: Defining web components...');
    customElements.define('sandbox-history-element', SandboxHistoryElement);
}