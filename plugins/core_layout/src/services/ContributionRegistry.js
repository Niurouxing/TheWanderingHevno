// plugins/core_layout/src/services/ContributionRegistry.js

/**
 * 负责收集、解析和管理所有插件的声明式贡献。
 * 这个类是实现“声明式贡献，而非命令式注入”哲学的核心。
 */
export class ContributionRegistry {
    constructor() {
        this.manifests = [];
        this.processedContributions = {
            views: new Map(),
            commands: new Map(),
            menus: new Map(),
        };
    }

    registerManifest(manifest) {
        if (!manifest || !manifest.id) {
            console.warn('[Registry] Attempted to register an invalid manifest.');
            return;
        }
        if (manifest.frontend?.contributions) {
            this.manifests.push(manifest);
        }
    }

    processContributions() {
        const sortedManifests = [...this.manifests].sort((a, b) => 
            (b.frontend?.priority || 0) - (a.frontend?.priority || 0)
        );

        for (const manifest of sortedManifests) {
            const contributions = manifest.frontend.contributions;
            if (contributions.views) {
                this.processViewContributions(manifest, contributions.views);
            }
        }

        for (const [slot, views] of this.processedContributions.views.entries()) {
            views.sort((a, b) => (a.order || 0) - (b.order || 0));
        }
        console.log('[Registry] All contributions processed:', this.processedContributions);
    }
    
    processViewContributions(manifest, viewsContribution) {
        for (const [slotName, views] of Object.entries(viewsContribution)) {
            if (!this.processedContributions.views.has(slotName)) {
                this.processedContributions.views.set(slotName, []);
            }

            const existingViewsInSlot = this.processedContributions.views.get(slotName);
            
            for (const view of views) {
                if (!view.id || !view.component || view.component.indexOf('-') === -1) {
                    console.error(`[Registry] Invalid view contribution from plugin '${manifest.id}'.`, view);
                    continue;
                }

                const isOverridden = existingViewsInSlot.some(v => v.id === view.id);

                if (!isOverridden) {
                    const enrichedView = { ...view, pluginId: manifest.id };
                    existingViewsInSlot.push(enrichedView);
                } else {
                     console.log(`[Registry] View '${view.id}' in slot '${slotName}' from plugin '${manifest.id}' was overridden by a higher priority plugin.`);
                }
            }
        }
    }

    getViews(slotName) {
        return this.processedContributions.views.get(slotName) || [];
    }
}