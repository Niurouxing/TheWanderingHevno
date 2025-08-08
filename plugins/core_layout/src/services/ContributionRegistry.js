// plugins/core_layout/src/App.jsx
export class ContributionRegistry {
    constructor(manifestProvider) {
        this.pageComponents = [];
        this.manifests = manifestProvider.getManifests();
        this.processContributions();
    }

    processContributions() {
        // 我们只关心 'page-component' 类型的插件
        const pagePlugins = this.manifests.filter(
            m => m.frontend?.type === 'page-component' && m.frontend?.contributions?.pageComponents
        );

        for (const manifest of pagePlugins) {
            for (const pageDef of manifest.frontend.contributions.pageComponents) {
                if (pageDef.id && pageDef.componentExportName && pageDef.menu) {
                    this.pageComponents.push({
                        ...pageDef,
                        pluginId: manifest.id,
                        manifest: manifest, // 保存整个 manifest 以便后续查找入口文件
                    });
                } else {
                    console.warn(`[core_layout] Invalid pageComponent contribution from plugin '${manifest.id}'.`, pageDef);
                }
            }
        }
        console.log(`[core_layout] Discovered ${this.pageComponents.length} page components.`, this.pageComponents);
    }

    getPageComponents() {
        return this.pageComponents;
    }
}