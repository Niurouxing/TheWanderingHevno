// plugins/core_layout/src/main.js

import { Layout } from './Layout.js';
import './styles.css';

// 导入本插件提供的所有应用层服务
import { ContributionRegistry } from './services/ContributionRegistry.js';
import { LayoutService } from './services/LayoutService.js';
import { RendererService } from './services/RendererService.js';

/**
 * 核心布局与应用主控插件的注册入口。
 * @param {object} context - 由内核加载器注入的，只包含最底层服务的 ServiceContainer。
 */
export function registerPlugin(context) {
    console.log('[core_layout] Registering as Application Host...');
    
    // 1. 注册本插件提供的“应用层”服务
    const contributionRegistry = new ContributionRegistry();
    context.register('contributionRegistry', contributionRegistry, 'core_layout');

    const layoutService = new LayoutService();
    context.register('layoutService', layoutService, 'core_layout');
    
    const rendererService = new RendererService(context);
    context.register('rendererService', rendererService, 'core_layout');
    
    const hookManager = context.get('hookManager');
    if (!hookManager) {
        console.error('[core_layout] CRITICAL: HookManager service not found in context!');
        return;
    }

    // 2. 监听内核加载器发出的“就绪”信号，然后接管应用的启动流程
    hookManager.addImplementation('loader.ready', async () => {
        console.log('[core_layout] Received "loader.ready" signal. Starting application bootstrap...');
        
        // a. 从 ManifestProvider 获取所有插件的清单
        const manifestProvider = context.get('manifestProvider');
        if (!manifestProvider) {
            console.error('[core_layout] CRITICAL: ManifestProvider service not found!');
            return;
        }
        const allManifests = manifestProvider.getManifests();

        // b. 注册并处理所有插件的贡献
        allManifests.forEach(manifest => {
            contributionRegistry.registerManifest(manifest);
        });
        contributionRegistry.processContributions();

        // c. 挂载UI骨架 (这会调用 layoutService.registerSlot)
        const layout = new Layout(document.getElementById('app'), context);
        layout.mount();

        // d. 调用渲染服务，将所有处理过的贡献渲染到已注册的插槽中
        await rendererService.renderAll();
        
        console.log('[core_layout] Application bootstrap complete. UI is ready.');
    });
}