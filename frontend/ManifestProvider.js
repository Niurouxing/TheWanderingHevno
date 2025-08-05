// /frontend/ManifestProvider.js

/**
 * 在插件加载期间收集所有前端插件的清单文件内容。
 * 这是一个无逻辑的数据容器，由内核填充，由应用主控插件消费。
 */
export class ManifestProvider {
    constructor() {
        this.manifests = [];
    }

    /**
     * 由内核在加载每个插件时调用。
     * @param {object} manifest - 一个插件的 manifest.json 内容。
     */
    addManifest(manifest) {
        this.manifests.push(manifest);
    }

    /**
     * 由应用主控插件调用，以获取所有已加载插件的清单。
     * @returns {Array<object>}
     */
    getManifests() {
        return this.manifests;
    }
}