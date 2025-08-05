// plugins/core_diagnostics/src/main.jsx
import React from 'react';
import { createRoot } from 'react-dom/client';

// 导入所有 Web Component 封装器
import { ConnectionStatusElement } from './views/ConnectionStatusElement.jsx';
import { SandboxIndicatorElement } from './views/SandboxIndicatorElement.jsx';
import { PluginListElement } from './views/PluginListElement.jsx';

// 导入用于动态渲染的组件
import { SystemReportView } from './components/SystemReportView.jsx';

/**
 * 核心诊断插件的注册入口。
 * @param {object} context - 由内核加载器注入的，包含底层服务的 ServiceContainer 实例。
 */

export function registerPlugin(context) {
    // Stage 1
    console.log('[core_diagnostics] Stage 1: Defining web components...');
    customElements.define('connection-status-element', ConnectionStatusElement);
    customElements.define('sandbox-indicator-element', SandboxIndicatorElement);
    customElements.define('plugin-list-element', PluginListElement);
    console.log('[core_diagnostics] Stage 1: All web components defined.');

    const hookManager = context.get('hookManager');
    if (!hookManager) { return; }

    // Stage 2: ++ 修改，监听 host.ready
    hookManager.addImplementation('host.ready', () => {
        console.log('[core_diagnostics] Stage 2: "host.ready" received. Registering command handlers...');
        
        const commandService = context.get('commandService');
        const layoutService = context.get('layoutService');

        if (commandService && layoutService) {
            commandService.registerHandler(
                'developer.showSystemReport',
                async () => {
                    console.log('[core_diagnostics] Executing command: developer.showSystemReport');
                    const panelSlot = layoutService.addPanel('bottom', { id: 'system-report', title: 'System Report' });
                    if (panelSlot) {
                        const reactRoot = createRoot(panelSlot);
                        reactRoot.render(<React.StrictMode><SystemReportView /></React.StrictMode>);
                    }
                }
            );
        } else {
            console.error('[core_diagnostics] CRITICAL: Services not available even after "host.ready".');
        }
    });
}