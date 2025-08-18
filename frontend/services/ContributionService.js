// frontend/services/ContributionService.js

/**
 * 一个核心服务，负责在应用启动时收集所有插件的清单文件(manifest)中定义的"贡献"，
 * 并按"贡献点"将它们组织起来。
 * 
 * 它是实现前端插件化解耦的关键。任何插件都可以通过查询此服务来发现其他插件提供的扩展功能。
 */
export class ContributionService {
  constructor() {
    /**
     * @type {Map<string, object[]>}
     * K: 贡献点ID (e.g., 'core_layout.pages')
     * V: 该贡献点的所有贡献对象数组
     */
    this.contributionsByPoint = new Map();
  }

  /**
   * 在应用启动时，由前端加载器调用一次。
   * 负责遍历所有插件清单，解析其贡献，并填充内部存储。
   * @param {object[]} manifests - 所有已加载插件的 manifest.json 内容数组。
   */
  processManifests(manifests) {
    console.log('[ContributionService] 开始处理所有插件清单的贡献...');
    
    for (const manifest of manifests) {
      const contributions = manifest.frontend?.contributions;
      if (!contributions || typeof contributions !== 'object') {
        continue; // 该插件没有提供任何贡献
      }

      // 遍历一个插件提供的所有贡献点 (e.g., 'core_layout.pages', 'frontend.host')
      for (const pointId in contributions) {
        if (!this.contributionsByPoint.has(pointId)) {
          this.contributionsByPoint.set(pointId, []);
        }

        const contributionsForPoint = this.contributionsByPoint.get(pointId);
        const pluginContributions = contributions[pointId];

        if (Array.isArray(pluginContributions)) {
          for (const contribution of pluginContributions) {
            // [关键] 将贡献来源的插件ID和整个manifest附加到贡献对象上，以便消费者知道它来自哪里
            const enrichedContribution = { ...contribution, pluginId: manifest.id, manifest: manifest };
            contributionsForPoint.push(enrichedContribution);
          }
        }
      }
    }
    console.log(`[ContributionService] 处理完成。发现 ${this.contributionsByPoint.size} 个贡献点。`);
  }

  /**
   * 插件和核心服务使用的主要查询方法。
   * @param {string} pointId - 唯一的贡献点ID。
   * @returns {object[]} - 一个包含所有为该点提供的贡献对象的数组，如果不存在则返回空数组。
   */
  getContributionsFor(pointId) {
    return this.contributionsByPoint.get(pointId) || [];
  }

  /**
   * (辅助方法) 获取所有已注册的贡献点ID。
   * @returns {string[]}
   */
  getAllContributionPoints() {
    return Array.from(this.contributionsByPoint.keys());
  }
}
