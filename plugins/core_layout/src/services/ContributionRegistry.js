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
            if (contributions.views) {
                this.processViewContributions(manifest, contributions.views);
            }
            if (contributions.commands) {
                this.processCommandContributions(manifest, contributions.commands, context);
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

    processCommandContributions(manifest, commandsContribution, context) {
        const commandService = context.get('commandService');
        if (!commandService) {
            console.error('[Registry] CommandService not available to process command contributions.');
            return;
        }

        for (const command of commandsContribution) {
            if (!command.id || !command.title) {
                console.error(`[Registry] Invalid command contribution from plugin '${manifest.id}'. 'id' and 'title' are required.`, command);
                continue;
            }

            // 从插件动态加载的模块中获取处理函数
            // 注意：这是一个简化的实现。一个更健壮的系统可能需要插件
            // 在 registerPlugin 时主动注册命令的 handler 函数。
            // 这里我们假设命令的 handler 是一个全局可访问的函数，或者需要更复杂的机制来定位。
            // 一个简单的约定是：插件在 `registerPlugin` 时将 command handlers 挂载到某个地方。
            // 为简单起见，我们暂时将 handler 定义为字符串，由调用方解析。
            
            // 为了演示，我们暂时不实现 handler 的动态绑定，只注册命令本身
            // 完整的 handler 绑定需要在插件的 JS 入口文件中完成
            const commandToRegister = {
                title: command.title,
                handler: () => { 
                    // 真正的 handler 应该由插件在 JS 中提供，并通过 Hook 或 Service 关联起来
                    console.log(`Placeholder for command '${command.id}' from plugin '${manifest.id}'`);
                    alert(`Executing: ${command.title}`);
                }
            };

            commandService.register(command.id, commandToRegister, manifest.id);
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