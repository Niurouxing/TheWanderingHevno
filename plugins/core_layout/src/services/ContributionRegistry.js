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
        const sortedManifests = [...this.manifests].sort((a, b) => 
            (b.frontend?.priority || 0) - (a.frontend?.priority || 0)
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
                // ++ 修改：现在只处理元数据
                this.processCommandContributions(manifest, contributions.commands, context);
            }
        }

        for (const [slot, views] of this._processedContributions.views.entries()) {
            views.sort((a, b) => (a.order || 0) - (b.order || 0));
        }
        console.log('[Registry] All contributions processed:', this._processedContributions);
    }
    
    processViewContributions(manifest, viewsContribution) {
        // [DEBUG] 日志注入点 4: 进入子函数
        console.log(`%c[DEBUG|Registry]   -> Inside processViewContributions for ${manifest.id}`, 'color: cyan;');
        console.log(`[DEBUG|Registry]      viewsContribution object received:`, JSON.parse(JSON.stringify(viewsContribution)));

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

    processCommandContributions(manifest, commandsContribution, context) {
        const commandService = context.get('commandService');
        if (!commandService) return;

        for (const command of commandsContribution) {
            if (!command.id || !command.title) {
                console.error(`[Registry] Invalid command contribution from plugin '${manifest.id}'.`, command);
                continue;
            }
            // 只注册元数据，不涉及 handler
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