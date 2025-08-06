// plugins/core_layout/src/main.js

import { Layout } from './Layout.js';

// 导入本插件提供的所有应用层服务
import { ContributionRegistry } from './services/ContributionRegistry.js';
import { LayoutService } from './services/LayoutService.js';
import { RendererService } from './services/RendererService.js';
import { CommandService } from './services/CommandService.js';

// =================================================================
// 关键修复: 添加一个全局标志位来防止重复初始化
// =================================================================
// 我们将标志位挂载到 window 对象上，以确保它在模块重载后依然存在。
if (typeof window.hevnoCoreLayoutInitialized === 'undefined') {
  window.hevnoCoreLayoutInitialized = false;
}
// =================================================================

export function registerPlugin(context) {
    // 关键修复: 在函数入口检查标志位
    if (window.hevnoCoreLayoutInitialized) {
        console.warn('[core_layout] Attempted to re-register. Aborting to prevent duplication.');
        return;
    }
    
    console.log('[core_layout] Registering as Application Host for the first time...');
    
    // 1. 注册本插件提供的“应用层”服务
    // 这个逻辑现在是安全的，因为它只会被执行一次。
    context.register('contributionRegistry', new ContributionRegistry(), 'core_layout');
    context.register('layoutService', new LayoutService(), 'core_layout');
    context.register('rendererService', new RendererService(context), 'core_layout');
    context.register('commandService', new CommandService(), 'core_layout');

    const hookManager = context.get('hookManager');
    if (!hookManager) {
        console.error('[core_layout] CRITICAL: HookManager service not found!');
        return;
    }

    // 2. 监听内核加载器发出的“就绪”信号
    hookManager.addImplementation('loader.ready', async () => {
        // 再次检查，双重保险
        if (window.hevnoCoreLayoutInitialized) {
            return;
        }
        // 设置标志位，表明初始化已开始
        window.hevnoCoreLayoutInitialized = true;
        
        console.log('[core_layout] Received "loader.ready". Starting application bootstrap...');
        
        const manifestProvider = context.get('manifestProvider');
        const contributionRegistry = context.get('contributionRegistry');
        const rendererService = context.get('rendererService');

        // a. 注册并处理所有插件的贡献
        const allManifests = manifestProvider.getManifests();
        contributionRegistry.registerManifests(allManifests);
        contributionRegistry.processContributions(context);

        // b. 挂载UI骨架
        const layout = new Layout(document.getElementById('app'), context);
        layout.mount();

        // c. 调用渲染服务
        await rendererService.renderAll();
        
        console.log('[core_layout] Application bootstrap complete. UI is ready.');

        // d. 触发 host.ready 钩子
        console.log('[core_layout] Triggering "host.ready" for other plugins...');
        await hookManager.trigger('host.ready');
    });
}