// /frontend/main.js
import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';
import { ContributionRegistry } from './ContributionRegistry.js';
import { ServiceContainer } from './ServiceContainer.js';

class FrontendKernel {
  constructor() {
    this.services = new ServiceContainer();

    // 注册最核心的服务
    this.hookManager = new HookManager();
    this.services.register('hookManager', this.hookManager, 'kernel');
    
    this.contributionRegistry = new ContributionRegistry();
    this.services.register('contributionRegistry', this.contributionRegistry, 'kernel');
    
    // 【修改】将服务容器正式暴露为全局服务定位器
    // 这并非一个随意的全局变量，而是一个明确的架构决策，为所有插件提供一个稳定的服务获取入口。
    window.Hevno = {
      services: this.services
    };

    // 【保留】为了方便调试，保留旧的别名
    if (import.meta.env.DEV) {
      window.hevno = this.services;
    }
  }

  async start() {
    console.log("🚀 Hevno Frontend Kernel starting...");

    // 【修改】初始化并注册 RemoteHookProxy
    const remoteProxy = new RemoteHookProxy(this.hookManager);
    this.services.register('remoteProxy', remoteProxy, 'kernel');
    remoteProxy.connect();

    // 【修改】将整个 service container 作为 context 传递
    const kernelContext = this.services; 

    // ... fetch 和加载插件的逻辑保持不变 ...
    try {
      const response = await fetch('/api/plugins/manifest');
      if (!response.ok) {
          throw new Error(`Failed to fetch manifest: ${response.statusText}`);
      }
      const allManifests = await response.json();

      const frontendPlugins = allManifests.filter(m => m.frontend);

      console.log(`Found ${frontendPlugins.length} frontend plugins to load:`, frontendPlugins.map(p => p.id));

      for (const manifest of frontendPlugins) {
        // ... 注册清单到 Registry 的逻辑不变
        this.contributionRegistry.registerManifest(manifest);

        try {
          const entryPointUrl = `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;
          const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            console.log(`-> Registering plugin: ${manifest.id}`);
            // 【修改】现在传递的是 ServiceContainer 实例
            await Promise.resolve(pluginModule.registerPlugin(kernelContext));
          }
        } catch (e) {
          console.error(`Failed to load or register plugin ${manifest.id}:`, e);
        }
      }

      // ... 后续逻辑保持不变 ...
      console.log("Processing all registered contributions...");
      this.contributionRegistry.processContributions();

    } catch (e) {
      console.error("Fatal: Could not initialize plugins.", e);
      document.getElementById('app').innerHTML = `<div style="color: red; padding: 2rem;">Error: Could not load plugin manifests from backend. Is the backend server running?</div>`;
      return;
    }

    console.log("All plugins registered. Mounting application layout...");
    await this.hookManager.trigger('layout.mount', { target: document.getElementById('app') });
    console.log("✅ Hevno Frontend is ready.");
  }
}

// 启动内核
const kernel = new FrontendKernel();
kernel.start();