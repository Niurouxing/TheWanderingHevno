// plugins/core_layout/src/services/ContributionRegistry.js
export class ContributionRegistry {
    /**
     * [核心修改] 构造函数现在接收 contributionService 实例。
     * @param {import('../../../../../frontend/services/ContributionService').ContributionService} contributionService
     */
    constructor(contributionService) {
        this.contributionService = contributionService;
        this.pageComponents = [];
        this.processContributions();
    }

    processContributions() {
        // [核心修改] 不再需要手动遍历和筛选 manifests。
        // 直接向 ContributionService 查询 'core_layout.pages' 贡献点的所有贡献。
        const pageContributions = this.contributionService.getContributionsFor('core_layout.pages');
        
        for (const contribution of pageContributions) {
            // 进行基本的验证
            if (contribution.id && contribution.componentExportName) {
                this.pageComponents.push({
                    ...contribution,
                    // 'pluginId' 和 'manifest' 已经由 ContributionService 附加
                });
            } else {
                console.warn(`[core_layout] Invalid page contribution from plugin '${contribution.pluginId}'. Missing 'id' or 'componentExportName'.`, contribution);
            }
        }
        
        console.log(`[core_layout] Discovered ${this.pageComponents.length} page components via ContributionService.`, this.pageComponents);
    }

    getPageComponents() {
        return this.pageComponents;
    }
}