// frontend/packages/kernel/main.ts

import { ServiceRegistry } from './ServiceRegistry';
import { PluginService } from './PluginService';

// 伪 APIService 用于启动
const apiService = { get: (url: string) => fetch(url).then(res => res.json()) };

// 1. 初始化所有内核服务
const serviceRegistry = new ServiceRegistry();
const pluginService = new PluginService(apiService);

// 2. 在 window 上创建全局命名空间
(window as any).Hevno = {
  services: {
    registry: serviceRegistry,
    plugins: pluginService,
    api: apiService,
  }
};

// 3. 将自身注册到注册表中
serviceRegistry.register('registry', serviceRegistry);
serviceRegistry.register('plugins', pluginService);

// 4. 在 DOMContentLoaded 后启动插件加载流程
document.addEventListener('DOMContentLoaded', () => {
    // 确保根元素存在
    if (!document.getElementById('hevno-root')) {
        const root = document.createElement('div');
        root.id = 'hevno-root';
        document.body.appendChild(root);
    }
    pluginService.loadPlugins();
});