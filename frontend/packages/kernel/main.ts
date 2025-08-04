// frontend/packages/kernel/main.ts (更新后)
import { ServiceRegistry } from './src/ServiceRegistry';
import { PluginService } from './src/PluginService';
import { ServiceBus } from './src/ServiceBus';
import { HookSystem } from './src/HookSystem';
import { APIService } from './src/APIService';

// 1. 初始化所有内核服务
const registry = new ServiceRegistry();
const bus = new ServiceBus();
const hooks = new HookSystem();
const api = new APIService();
const plugins = new PluginService(api, hooks); // PluginService需要钩子来触发事件

// 2. 在 window 上创建全局命名空间
(window as any).Hevno = {
  services: { registry, bus, hooks, api, plugins }
};

// 3. 将自身注册到注册表中，供插件使用
registry.register('registry', registry);
registry.register('bus', bus);
registry.register('hooks', hooks);
registry.register('api', api);
registry.register('plugins', plugins);

// 4. 在 DOMContentLoaded 后启动插件加载流程
document.addEventListener('DOMContentLoaded', () => {
    const rootEl = document.getElementById('hevno-root') || (() => {
        const root = document.createElement('div');
        root.id = 'hevno-root';
        document.body.appendChild(root);
        return root;
    })();
    
    // 在加载插件前，可以先触发一个内核就绪的钩子
    hooks.trigger('kernel:ready', { rootEl }).then(() => {
        plugins.loadPlugins();
    });
});