// /frontend/ServiceContainer.js

/**
 * 一个简单的依赖注入(DI)容器，用于管理单例服务。
 * 确保服务的注册、获取和覆盖是明确且可追踪的。
 */
export class ServiceContainer {
    constructor() {
        this.serviceInstances = new Map();
        this.serviceProviders = new Map(); // 用于追踪哪个插件提供了服务
    }

    /**
     * 向容器注册一个服务实例。
     * @param {string} serviceName - 服务的唯一名称。
     * @param {*} serviceInstance - 服务的实例。
     * @param {string} pluginId - 提供此服务的插件ID。
     */
    register(serviceName, serviceInstance, pluginId) {
        if (this.serviceInstances.has(serviceName)) {
            const originalProvider = this.serviceProviders.get(serviceName);
            console.warn(`[Services] Service '${serviceName}' (provided by '${originalProvider}') is being overridden by plugin '${pluginId}'.`);
        }
        this.serviceInstances.set(serviceName, serviceInstance);
        this.serviceProviders.set(serviceName, pluginId);
        console.log(`[Services] Service '${serviceName}' registered by plugin '${pluginId}'.`);
    }

    /**
     * 从容器中获取一个服务实例。
     * @param {string} serviceName - 服务的名称。
     * @returns {*} 服务实例，如果不存在则返回 undefined。
     */
    get(serviceName) {
        const service = this.serviceInstances.get(serviceName);
        if (!service) {
            // 在开发中，这是一个有用的警告，可以帮助快速定位问题。
            console.warn(`[Services] Service '${serviceName}' was requested but has not been registered.`);
        }
        return service;
    }

    /**
     * 检查一个服务是否已被注册。
     * @param {string} serviceName - 服务的名称。
     * @returns {boolean}
     */
    has(serviceName) {
        return this.serviceInstances.has(serviceName);
    }
}