import { useMemo } from 'react';

/**
 * 一个自定义 React Hook，用于从 Hevno 全局服务容器中获取服务。
 * @param {string} serviceName - 要获取的服务的名称。
 * @returns {*} 服务实例，如果不存在则返回 undefined。
 */
export function useService(serviceName) {
    const service = useMemo(() => {
        // 使用服务定位器模式从全局窗口对象获取服务
        const services = window.Hevno?.services;
        if (!services) {
            console.error(`[useService] Hevno service container (window.Hevno.services) not found. Was the loader not started?`);
            return undefined;
        }
        
        const instance = services.get(serviceName);
        if (!instance) {
            // 在开发模式下，这会帮助快速定位问题
            console.warn(`[useService] Service '${serviceName}' was requested but is not available.`);
        }
        return instance;

    }, [serviceName]); // 仅在 serviceName 改变时重新计算

    return service;
}