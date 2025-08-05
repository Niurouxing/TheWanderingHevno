// /frontend/main.js
import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';
import { ContributionRegistry } from './ContributionRegistry.js'; // <-- 1. 导入

class FrontendKernel {
  constructor() {
    // 2. 初始化所有核心服务
    this.hookManager = new HookManager();
    this.contributionRegistry = new ContributionRegistry();
    
    this.services = {
        hookManager: this.hookManager,
        contributionRegistry: this.contributionRegistry, // <-- 暴露给插件
    };

    if (import.meta.env.DEV) {
      window.hevno = this.services;
    }
  }

  async start() {
    console.log("🚀 Hevno Frontend Kernel starting...");

    // 初始化 WebSocket 代理
    const remoteProxy = new RemoteHookProxy(this.hookManager);
    this.services.remoteProxy = remoteProxy;
    remoteProxy.connect();

    const kernelContext = this.services; 

    // 获取并加载所有前端插件
    try {
      const response = await fetch('/api/plugins/manifest');
      if (!response.ok) {
          throw new Error(`Failed to fetch manifest: ${response.statusText}`);
      }
      const allManifests = await response.json();

      const frontendPlugins = allManifests
        .filter(m => m.frontend);
        // 不在这里排序了，让 Registry 来处理

      console.log(`Found ${frontendPlugins.length} frontend plugins to load:`, frontendPlugins.map(p => p.id));

      for (const manifest of frontendPlugins) {
        // 3. 注册每个插件的清单到 Registry
        this.contributionRegistry.registerManifest(manifest);

        try {
          const entryPointUrl = `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;
          const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            console.log(`-> Registering plugin: ${manifest.id}`);
            await Promise.resolve(pluginModule.registerPlugin(kernelContext));
          }
        } catch (e) {
          console.error(`Failed to load or register plugin ${manifest.id}:`, e);
        }
      }

      // 4. 所有插件加载并注册完毕后，处理所有贡献
      console.log("Processing all registered contributions...");
      this.contributionRegistry.processContributions();

    } catch (e) {
      console.error("Fatal: Could not initialize plugins.", e);
      document.getElementById('app').innerHTML = `<div style="color: red; padding: 2rem;">Error: Could not load plugin manifests from backend. Is the backend server running?</div>`;
      return;
    }

    // 5. 触发应用挂载钩子
    console.log("All plugins registered. Mounting application layout...");
    await this.hookManager.trigger('layout.mount', { target: document.getElementById('app') });
    console.log("✅ Hevno Frontend is ready.");
  }
}

// 启动内核
const kernel = new FrontendKernel();
kernel.start();