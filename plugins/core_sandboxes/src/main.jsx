// plugins/core_sandboxes/src/main.jsx
import React from 'react';
import { createRoot } from 'react-dom/client';

// 导入 Web Component 封装器
import { SandboxListElement } from './views/SandboxListElement.jsx';
// ++ 导入新的创建视图组件
import { CreateSandboxView } from './components/CreateSandboxView.jsx';

// 遵循插件开发黄金规则一：严格遵循两阶段初始化
export function registerPlugin(context) {
    // ---------------------------------
    // 阶段一: 同步注册 Web Component
    // ---------------------------------
    console.log('[core_sandboxes] Stage 1: Defining web components...');
    customElements.define('sandbox-list-element', SandboxListElement);
    console.log('[core_sandboxes] Stage 1: Web component defined.');

    const hookManager = context.get('hookManager');
    if (!hookManager) { return; }

    // ---------------------------------
    // 阶段二: 注册 host.ready 监听器，以附加命令处理器等
    // ---------------------------------
    hookManager.addImplementation('host.ready', () => {
        console.log('[core_sandboxes] Stage 2: "host.ready" received. Registering command handlers...');
        
        const commandService = context.get('commandService');
        const layoutService = context.get('layoutService');

        if (commandService && layoutService) {
            commandService.registerHandler(
                'sandboxes.create',
                async () => {
                    console.log("[core_sandboxes] Executing command: sandboxes.create");
                    // ++ 获取主视图插槽
                    const mainViewSlot = layoutService.getSlot('workbench.main.view');
                    if (mainViewSlot) {
                        // 清空主视图并渲染创建表单
                        mainViewSlot.innerHTML = '';
                        const reactRoot = createRoot(mainViewSlot);
                        reactRoot.render(
                            <React.StrictMode>
                                <CreateSandboxView />
                            </React.StrictMode>
                        );
                    } else {
                        console.error("[core_sandboxes] Could not find 'workbench.main.view' slot.");
                    }
                }
            );
        }
    });
}