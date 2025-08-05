// plugins/core_sandboxes/src/main.jsx

// 导入 Web Component 封装器
import { SandboxListElement } from './views/SandboxListElement.jsx';

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
        if (commandService) {
            commandService.registerHandler(
                'sandboxes.create',
                async () => {
                    // TODO: 实现创建沙盒的逻辑，例如打开一个模态框或新视图
                    alert("Command 'sandboxes.create' executed! UI not yet implemented.");
                    console.log("[core_sandboxes] Executing command: sandboxes.create");
                }
            );
        }
    });
}