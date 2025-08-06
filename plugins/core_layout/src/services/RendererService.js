// plugins/core_layout/src/services/RendererService.js

/**
 * 负责将已解析的UI贡献渲染到由 LayoutService 注册的插槽中。
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
        // 逻辑保持不变，它能优雅地处理只有一个贡献点的情况
        for (const [slotName, views] of contributionRegistry.getProcessedContributions().views.entries()) {
            const targetSlot = layoutService.getSlot(slotName);
            if (targetSlot) {
                for (const view of views) {
                    renderTasks.push(this.renderView(view, targetSlot));
                }
            } else {
                console.warn(`[RendererService] Slot '${slotName}' not found for rendering view '${view.id}'.`);
            }
        }
        await Promise.all(renderTasks);
        console.log('[RendererService] All contributions rendered.');
    }

    /**
     * 将单个视图（Web Component）渲染到目标插槽中。
     * @param {object} view - 已处理的视图贡献对象
     * @param {HTMLElement} targetSlot - 要渲染到的 DOM 元素
     */
    async renderView(view, targetSlot) {
        try {
            // 等待自定义元素被定义，防止 race condition
            await customElements.whenDefined(view.component);
            const componentElement = document.createElement(view.component);
            
            // 关键变更: 移除了为视图创建带标题的包装容器的特殊逻辑。
            // 现在的逻辑是通用的：直接将组件附加到插槽中。
            // 这对于渲染像 Goliath 这样的根级应用组件是完美的。
            targetSlot.appendChild(componentElement);

            console.log(`[RendererService] Rendered component <${view.component}> (from plugin '${view.pluginId}') into slot '${targetSlot.id}'.`);

        } catch (e) {
            console.error(`[RendererService] Failed to create or mount element '${view.component}' from plugin '${view.pluginId}'.`, e);
        }
    }
}