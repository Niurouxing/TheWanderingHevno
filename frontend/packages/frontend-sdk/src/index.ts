// frontend/packages/frontend-sdk/src/index.ts

// 导出核心 React Hooks
export { useService } from './hooks/useService';
export { useEvent } from './hooks/useEvent';
export { useApi } from './hooks/useApi';

// 重新导出所有类型定义，方便插件开发者导入
export * from './types'; 

// 导出插件定义函数
export { definePlugin } from './definePlugin';

// 导出一个方便访问核心服务的对象
import { HevnoGlobal } from './types';

const getHevno = (): HevnoGlobal | undefined => (window as any).Hevno;

export const services = {
  get api() { return getHevno()?.services.api!; },
  get bus() { return getHevno()?.services.bus!; },
  get hooks() { return getHevno()?.services.hooks!; },
  get registry() { return getHevno()?.services.registry!; },
  get plugins() { return getHevno()?.services.plugins!; },
};