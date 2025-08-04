import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';

class FrontendKernel {
  constructor() {
    this.hookManager = new HookManager();
    // 在开发模式下，将核心服务暴露到全局，方便调试
    if (import.meta.env.DEV) {
      window.hevno = {
        hookManager: this.hookManager,
      };
    }
  }

  async start() {
    console.log("🚀 Hevno Frontend Kernel starting...");

    // 1. 初始化核心服务
    const remoteProxy = new RemoteHookProxy(this.hookManager);
    remoteProxy.connect();
    if (import.meta.env.DEV) {
      window.hevno.remoteProxy = remoteProxy;
    }

    const kernelContext = {
      hookManager: this.hookManager,
      remoteProxy: remoteProxy,
    };

    // 2. 获取并加载所有前端插件
    try {
      const response = await fetch('/api/plugins/manifest');
      if (!response.ok) {
          throw new Error(`Failed to fetch manifest: ${response.statusText}`);
      }
      const allManifests = await response.json();

      const frontendPlugins = allManifests
        .filter(m => m.frontend)
        .sort((a, b) => (a.frontend.priority || 0) - (b.frontend.priority || 0));

      console.log(`Found ${frontendPlugins.length} frontend plugins to load:`, frontendPlugins.map(p => p.id));

      for (const manifest of frontendPlugins) {
        try {
          // 后端通过 /plugins/{plugin_id}/{resource_path} 提供服务
          const entryPointUrl = `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;
          
          // 使用动态导入加载插件模块
          const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            console.log(`-> Registering plugin: ${manifest.id}`);
            // 注入核心上下文，让插件注册自己
            await Promise.resolve(pluginModule.registerPlugin(kernelContext));
          }
        } catch (e) {
          console.error(`Failed to load or register plugin ${manifest.id}:`, e);
        }
      }
    } catch (e) {
      console.error("Fatal: Could not initialize plugins.", e);
      document.getElementById('app').innerHTML = `<div style="color: red; padding: 2rem;">Error: Could not load plugin manifests from backend. Is the backend server running?</div>`;
      return;
    }

    // 3. 所有插件注册完毕，触发应用挂载钩子
    console.log("All plugins registered. Mounting application layout...");
    await this.hookManager.trigger('layout.mount', { target: document.getElementById('app') });
    console.log("✅ Hevno Frontend is ready.");
  }
}

// 启动内核
const kernel = new FrontendKernel();
kernel.start();