// plugins/core_layout/src/services/ContributionRegistry.js

/**
 * 负责收集、解析和管理所有插件的声明式贡献。
 * 这个类是实现“声明式贡献，而非命令式注入”哲学的核心。
 */
export class ContributionRegistry {
    constructor() {
        this.manifests = [];
        this._processedContributions = {
            views: new Map(),
            commands: new Map(),
            menus: new Map(),
        };
    }

    registerManifests(manifests) {
        for (const manifest of manifests) {
            if (manifest && manifest.id && manifest.frontend?.contributions) {
                this.manifests.push(manifest);
            }
        }
    }

    processContributions(context) {
        // ++ 核心修改：按优先级升序排序，与加载顺序一致
        const sortedManifests = [...this.manifests].sort((a, b) => 
            (a.frontend?.priority || 0) - (b.frontend?.priority || 0) 
        );

        for (const manifest of sortedManifests) {
            const contributions = manifest.frontend.contributions;
            if (!contributions) {
                continue; // 跳过没有贡献的插件
            }

            if (contributions.views) {
                this.processViewContributions(manifest, contributions.views);
            }
            if (contributions.commands) {
                this.processCommandContributions(manifest, contributions.commands, context);
            }
        }
        
        // ++ 核心修改：现在在所有贡献处理完后，再对每个槽位进行排序
        for (const [slot, views] of this._processedContributions.views.entries()) {
            views.sort((a, b) => (a.order || 0) - (b.order || 0));
        }
        console.log('[Registry] All contributions processed:', this._processedContributions);
    }
    
    processViewContributions(manifest, viewsContribution) {
        for (const [slotName, views] of Object.entries(viewsContribution)) {
            if (!this._processedContributions.views.has(slotName)) {
                this._processedContributions.views.set(slotName, []);
            }

            const existingViewsInSlot = this._processedContributions.views.get(slotName);
            
            for (const view of views) {
                if (!view.id || !view.component || view.component.indexOf('-') === -1) {
                    console.error(`[Registry] Invalid view contribution from plugin '${manifest.id}'.`, view);
                    continue;
                }
                
                // ++ 核心修改：实现覆盖逻辑
                // 查找是否已存在同ID的视图
                const existingViewIndex = existingViewsInSlot.findIndex(v => v.id === view.id);
                const enrichedView = { ...view, pluginId: manifest.id };

                if (existingViewIndex !== -1) {
                    // 如果存在，则用当前插件（更高优先级的）的贡献替换它
                    console.log(`[Registry] Overriding view '${view.id}' in slot '${slotName}' with contribution from plugin '${manifest.id}'.`);
                    existingViewsInSlot[existingViewIndex] = enrichedView;
                } else {
                    // 如果不存在，则直接添加
                    existingViewsInSlot.push(enrichedView);
                }
            }
        }
    }

    processCommandContributions(manifest, commandsContribution, context) {
        const commandService = context.get('commandService');
        if (!commandService) return;

        for (const command of commandsContribution) {
            if (!command.id || !command.title) {
                console.error(`[Registry] Invalid command contribution from plugin '${manifest.id}'.`, command);
                continue;
            }
            // ++ 核心修改：总是注册或覆盖元数据
            // 因为后加载的插件优先级更高，所以它的元数据应该生效
            commandService.registerMetadata(command.id, { title: command.title }, manifest.id);
            this._processedContributions.commands.set(command.id, { ...command, pluginId: manifest.id });
        }
    }

    getViews(slotName) {
        return this.processedContributions.views.get(slotName) || [];
    }

    getProcessedContributions() {
        return this._processedContributions;
    }
}