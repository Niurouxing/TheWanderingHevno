// frontend/packages/frontend-sdk/src/index.ts

// 从内核获取服务的包装器
export { useService } from './hooks/useService';
export { useEvent } from './hooks/useEvent';
export { useApi } from './hooks/useApi';

// 类型定义 (可以是一个单独的文件)
export * from './types'; 

// 插件定义函数
export { definePlugin } from './definePlugin';

// 其他便捷API
import { HevnoGlobal } from './types';
const getHevno = (): HevnoGlobal => (window as any).Hevno;

export const services = {
  get api() { return getHevno().services.api; },
  get bus() { return getHevno().services.bus; },
  get hooks() { return getHevno().services.hooks; },
  // ...
};

export function registerComponent(name: string, component: React.ComponentType<any>) {
    // 这个函数在插件内部调用时，我们如何知道是哪个插件调用的？
    // 这是一个难题。一个简单的解决方案是，在 onLoad 的参数中传入一个上下文对象。
    // 我们暂时简化，通过一个hacky的方式实现。
    // 更好的方式是改造PluginService的生命周期调用，传入一个上下文。
    console.warn('registerComponent is a simplified implementation.');
    (window as any).Hevno.services.plugins.registerComponentForCurrentPlugin(name, component);
}