// frontend/packages/frontend-sdk/src/definePlugin.ts
import { PluginLifecycle } from './types';

// 关键改动：definePlugin 会将生命周期对象附加到一个全局临时变量上
// PluginService 在加载完脚本后会立即读取并清除这个变量。
export function definePlugin(lifecycle: PluginLifecycle): void {
  (window as any).__HEVNO_PENDING_PLUGIN__ = lifecycle;
}