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
        for (const [slotName, views] of contributionRegistry.getProcessedContributions().views.entries()) { // ++ 修改
            const targetSlot = layoutService.getSlot(slotName);
            if (targetSlot) {
                for (const view of views) {
                    renderTasks.push(this.renderView(view, targetSlot));
                }
            } else { // ++ 新增
                console.warn(`[RendererService] Slot '${slotName}' not found for rendering view '${view.id}'.`);
            }
        }
        await Promise.all(renderTasks);
        console.log('[RendererService] All views rendered.');
    }

    async renderView(view, targetSlot) {
        try {
            await customElements.whenDefined(view.component);
            const componentElement = document.createElement(view.component);
            
            // ++ 新增逻辑：如果视图贡献需要一个容器...
            if (view.title) {
                const container = document.createElement('div');
                // 使用在 styles.css 中已定义的样式
                container.className = 'sidebar-view-container'; 
                
                const titleElement = document.createElement('h3');
                titleElement.textContent = view.title;
                
                const componentSlot = document.createElement('div');
                componentSlot.className = 'component-slot';
                
                componentSlot.appendChild(componentElement);
                container.appendChild(titleElement);
                container.appendChild(componentSlot);
                
                targetSlot.appendChild(container);
                console.log(`[RendererService] Rendered '${view.component}' with title '${view.title}' into slot for '${view.id}'.`);
            } else {
                // -- 旧逻辑：如果不需要容器，则直接附加
                targetSlot.appendChild(componentElement);
                console.log(`[RendererService] Rendered '${view.component}' into slot for '${view.id}'.`);
            }
        } catch (e) {
            console.error(`[RendererService] Failed to create or mount element '${view.component}' from plugin '${view.pluginId}'.`, e);
        }
    }
}