// plugins/core_runner/src/main.jsx
import React, { useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { RunnerView } from './components/RunnerView.jsx';

export function registerPlugin(context) {
    const hookManager = context.get('hookManager');
    if (!hookManager) return;

    // ++ 使用一个变量来跟踪当前显示的沙盒ID
    let currentSandboxId = null;

    hookManager.addImplementation('host.ready', () => {
        const layoutService = context.get('layoutService');
        if (!layoutService) {
            console.error('[core_runner] LayoutService not available.');
            return;
        }

        hookManager.addImplementation('sandbox.selected', (sandbox) => {
            // ++ 优化：只有当选择的沙盒变化时才重渲染
            if (sandbox?.id === currentSandboxId) {
                console.log(`[core_runner] Sandbox '${sandbox.name}' is already active. Skipping re-render.`);
                return;
            }
            
            console.log(`[core_runner] Received 'sandbox.selected': ${sandbox.name}. Rendering view.`);
            currentSandboxId = sandbox?.id; // 更新当前ID
            
            const mainViewSlot = layoutService.getSlot('workbench.main.view');
            
            if (mainViewSlot) {
                mainViewSlot.innerHTML = '';
                if (sandbox) { // 确保 sandbox 对象存在
                    const reactRoot = createRoot(mainViewSlot);
                    reactRoot.render(
                        <React.StrictMode>
                            <RunnerView sandbox={sandbox} />
                        </React.StrictMode>
                    );
                }
            }
        });
    });
}