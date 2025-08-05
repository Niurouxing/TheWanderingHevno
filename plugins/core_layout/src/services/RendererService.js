// plugins/core_layout/src/services/RendererService.js

/**
 * 负责将已解析的UI贡献渲染到由布局插件注册的插槽中。
 */
export class RendererService {
    constructor(serviceContainer) {
        this.services = serviceContainer;
    }

    async renderAll() {
        console.log('[RendererService] Starting initial render of all contributions...');
        const contributionRegistry = this.services.get('contributionRegistry');
        const layoutService = this.services.get('layoutService');

        if (!contributionRegistry || !layoutService) {
            console.error('[RendererService] Missing required services (ContributionRegistry or LayoutService).');
            return;
        }

        const renderTasks = [];
        for (const [slotName, views] of contributionRegistry.processedContributions.views.entries()) {
            const targetSlot = layoutService.getSlot(slotName);
            if (targetSlot) {
                for (const view of views) {
                    renderTasks.push(this.renderView(view, targetSlot));
                }
            }
        }
        await Promise.all(renderTasks);
        console.log('[RendererService] All views rendered.');
    }

    async renderView(view, targetSlot) {
        try {
            await customElements.whenDefined(view.component);
            const componentElement = document.createElement(view.component);
            targetSlot.appendChild(componentElement);
            console.log(`[RendererService] Rendered '${view.component}' into slot for '${view.id}'.`);
        } catch (e) {
            console.error(`[RendererService] Failed to create or mount element '${view.component}' from plugin '${view.pluginId}'.`, e);
        }
    }
}