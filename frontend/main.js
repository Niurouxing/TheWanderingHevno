// /frontend/main.js

import { ServiceContainer } from './ServiceContainer.js';
import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';
import { ManifestProvider } from './ManifestProvider.js';

/**
 * Hevno 前端加载器 (内核)。
 * 职责被严格限定为：
 * 1. 初始化并提供最底层的、无业务逻辑的服务。
 * 2. 从后端获取插件清单，并按优先级加载它们。
 * 3. 触发一个 `loader.ready` 钩子，然后将控制权完全移交。
 */
class FrontendLoader {
  constructor() {
    this.services = new ServiceContainer();
    window.Hevno = { services: this.services };

    // 1. 初始化最底层的服务
    const hookManager = new HookManager();
    this.services.register('hookManager', hookManager, 'loader');
    
    const remoteProxy = new RemoteHookProxy(hookManager);
    this.services.register('remoteProxy', remoteProxy, 'loader');

    const manifestProvider = new ManifestProvider();
    this.services.register('manifestProvider', manifestProvider, 'loader');

    // 方便调试
    if (import.meta.env.DEV) {
      window.hevno = this.services;
    }
  }

  async load() {
    console.log("🚀 Hevno Frontend Loader starting...");
    this.services.get('remoteProxy').connect();

    const loaderContext = this.services;
    const manifestProvider = this.services.get('manifestProvider');

    try {
      // 2. 获取插件清单
      const response = await fetch('/api/plugins/manifest');
      if (!response.ok) {
        throw new Error(`Failed to fetch manifest: ${response.statusText}`);
      }
      let allManifests = await response.json();
      
      // 按前端声明的优先级降序排序插件
      const frontendPlugins = allManifests
        .filter(m => m.frontend && m.frontend.entryPoint) 
        .sort((a, b) => (b.frontend?.priority || 0) - (a.frontend?.priority || 0));

      console.log(`Found ${frontendPlugins.length} frontend plugins to load:`, frontendPlugins.map(p => p.id));

      // 3. 依次加载并注册所有插件
      for (const manifest of frontendPlugins) {
        // 将清单添加到 provider，供应用主控插件后续使用
        manifestProvider.addManifest(manifest);
        
        try {
          // 动态导入插件入口点
          const entryPointUrl = `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;
          const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            console.log(`-> Registering plugin: ${manifest.id} (priority: ${manifest.frontend?.priority || 0})`);
            // 将底层服务上下文注入每个插件
            await Promise.resolve(pluginModule.registerPlugin(loaderContext));
          }
        } catch (e) {
          console.error(`Failed to load or register plugin ${manifest.id}:`, e);
        }
      }

    } catch (e) {
      console.error("Fatal: Could not initialize plugins.", e);
      document.body.innerHTML = `<div style="color: red; padding: 2rem;">Error: Could not load plugin manifests from backend. Is the backend server running?</div>`;
      return;
    }

    // 4. 内核工作结束！触发最终钩子，移交控制权。
    console.log("✅ All plugins loaded. Handing over control to application plugins...");
    await this.services.get('hookManager').trigger('loader.ready');
  }
}

// 启动加载器
const loader = new FrontendLoader();
loader.load();