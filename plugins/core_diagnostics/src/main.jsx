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
 * 注册插件，定义所有 Web Components 并将命令的 handler 绑定到服务
 * @param {object} context - ServiceContainer 实例
 */
export function registerPlugin(context) {
    const commandService = context.get('commandService');
    const layoutService = context.get('layoutService');

    // 1. 定义所有由本插件贡献的 Web Components
    customElements.define('connection-status-element', ConnectionStatusElement);
    customElements.define('sandbox-indicator-element', SandboxIndicatorElement);
    customElements.define('plugin-list-element', PluginListElement);

    console.log('[core_diagnostics] All web components defined.');
    
    // 2. 注册命令的 handler
    if (commandService && layoutService) {
        commandService.register(
            'developer.showSystemReport', 
            {
                title: 'Developer: Show System Report',
                handler: async () => {
                    // 动态添加底部面板
                    const panelSlot = layoutService.addPanel('bottom', { 
                        id: 'system-report', 
                        title: 'System Report' 
                    });

                    if (panelSlot) {
                        // 将 React 组件渲染到动态创建的插槽中
                        const reactRoot = createRoot(panelSlot);
                        reactRoot.render(
                            <React.StrictMode>
                                <SystemReportView />
                            </React.StrictMode>
                        );
                    }
                }
            }, 
            'core_diagnostics'
        );
        console.log('[core_diagnostics] "showSystemReport" command handler registered.');
    } else {
        console.warn('[core_diagnostics] CommandService or LayoutService not available. Cannot register command handlers.');
    }
}