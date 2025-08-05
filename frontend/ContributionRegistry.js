// /frontend/ContributionRegistry.js

/**
 * 负责收集、解析和管理所有插件的声明式贡献。
 * 这个类是实现“声明式贡献，而非命令式注入”哲学的核心。
 */
export class ContributionRegistry {
    constructor() {
        // 存储原始清单数据
        this.manifests = [];
        // 按贡献类型存储解析和冲突解决后的贡献
        // e.g., this.processedContributions.views.get('workbench.sidebar') -> [view1, view2]
        this.processedContributions = {
            views: new Map(),
            commands: new Map(),
            menus: new Map(),
            // 未来可以轻松扩展其他贡献类型...
        };
    }

    /**
     * 注册一个插件的清单文件。内核在加载每个插件时调用此方法。
     * @param {object} manifest - 插件的 manifest.json 内容。
     */
    registerManifest(manifest) {
        if (!manifest || !manifest.id) {
            console.warn('[Registry] Attempted to register an invalid manifest.');
            return;
        }
        this.manifests.push(manifest);
    }

    /**
     * 在所有清单都注册后调用此方法。
     * 它会遍历所有清单，处理它们的贡献，并根据优先级解决冲突。
     */
    processContributions() {
        // 按优先级降序排序，高优先级的先处理
        const sortedManifests = [...this.manifests].sort((a, b) => 
            (b.frontend?.priority || 0) - (a.frontend?.priority || 0)
        );

        for (const manifest of sortedManifests) {
            const contributions = manifest.frontend?.contributions;
            if (!contributions) continue;

            // 处理视图贡献 (Views)
            if (contributions.views) {
                this.processViewContributions(manifest, contributions.views);
            }
            // 在此处理其他贡献类型 (Commands, Menus, etc.)
        }

        // 处理完后，对每个槽位的视图按其自身定义的 order 排序
        for (const [slot, views] of this.processedContributions.views.entries()) {
            views.sort((a, b) => (a.order || 0) - (b.order || 0));
        }

        console.log('[Registry] All contributions processed:', this.processedContributions);
    }

    /**
     * 解析视图贡献，并处理覆盖逻辑。
     * @param {object} manifest - 贡献来源插件的清单。
     * @param {object} viewsContribution - manifest 中 contributions.views 的内容。
     */
    processViewContributions(manifest, viewsContribution) {
        for (const [slotName, views] of Object.entries(viewsContribution)) {
            if (!this.processedContributions.views.has(slotName)) {
                this.processedContributions.views.set(slotName, []);
            }

            const existingViewsInSlot = this.processedContributions.views.get(slotName);
            
            for (const view of views) {
                // 健壮性检查
                if (!view.id || !view.component || view.component.indexOf('-') === -1) {
                    console.error(`[Registry] Invalid view contribution from plugin '${manifest.id}'. Missing 'id' or valid 'component'.`, view);
                    continue;
                }

                // **覆盖逻辑**: 检查此插槽中是否已有相同 ID 的视图。
                // 因为我们是按优先级降序处理的，所以第一个遇到的就是优先级最高的。
                const isOverridden = existingViewsInSlot.some(v => v.id === view.id);

                if (!isOverridden) {
                    // 添加额外元数据，方便消费者使用
                    const enrichedView = {
                        ...view,
                        pluginId: manifest.id, // 溯源
                    };
                    existingViewsInSlot.push(enrichedView);
                } else {
                     console.log(`[Registry] View '${view.id}' in slot '${slotName}' from plugin '${manifest.id}' was overridden by a higher priority plugin.`);
                }
            }
        }
    }

    /**
     * 获取指定插槽的视图贡献。
     * @param {string} slotName - 插槽名称，例如 'workbench.sidebar'。
     * @returns {Array<object>} 一个已排序且无冲突的视图对象数组。
     */
    getViews(slotName) {
        return this.processedContributions.views.get(slotName) || [];
    }
}