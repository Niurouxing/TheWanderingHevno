// plugins/core_layout/src/main.js

import { Layout } from './Layout.js';


// 导入本插件提供的所有应用层服务
import { ContributionRegistry } from './services/ContributionRegistry.js';
import { LayoutService } from './services/LayoutService.js';
import { RendererService } from './services/RendererService.js';
import { CommandService } from './services/CommandService.js';

export function registerPlugin(context) {
    console.log('[core_layout] Registering as Application Host...');
    
    // 1. 注册本插件提供的“应用层”服务
    const contributionRegistry = new ContributionRegistry();
    context.register('contributionRegistry', contributionRegistry, 'core_layout');

    const layoutService = new LayoutService();
    context.register('layoutService', layoutService, 'core_layout');
    
    const rendererService = new RendererService(context);
    context.register('rendererService', rendererService, 'core_layout');

    const commandService = new CommandService();
    context.register('commandService', commandService, 'core_layout');

    const hookManager = context.get('hookManager');
    if (!hookManager) {
        console.error('[core_layout] CRITICAL: HookManager service not found in context!');
        return;
    }

    // 2. 监听内核加载器发出的“就绪”信号，然后接管应用的启动流程
    hookManager.addImplementation('loader.ready', async () => {
        console.log('[core_layout] Received "loader.ready". Starting application bootstrap...');
        
        const manifestProvider = context.get('manifestProvider');
        const contributionRegistry = context.get('contributionRegistry');
        const rendererService = context.get('rendererService');

        // a. 注册并处理所有插件的贡献 (元数据处理)
        const allManifests = manifestProvider.getManifests();
        contributionRegistry.registerManifests(allManifests);
        contributionRegistry.processContributions(context);

        // b. 挂载UI骨架
        const layout = new Layout(document.getElementById('app'), context);
        layout.mount();

        // c. 调用渲染服务，渲染声明式UI
        await rendererService.renderAll();
        
        console.log('[core_layout] Application bootstrap complete. UI is ready.');

        // d. ++ 核心修改：触发 host.ready 钩子，通知其他插件可以开始了
        console.log('[core_layout] Triggering "host.ready" for other plugins...');
        await hookManager.trigger('host.ready');
    });
}