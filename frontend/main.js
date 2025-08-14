// frontend/main.js

import { ServiceContainer } from './ServiceContainer.js';
import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';
import { ManifestProvider } from './ManifestProvider.js';
import { GlobalHookRegistry } from './services/GlobalHookRegistry.js';

class FrontendLoader {
  constructor() {
    this.services = new ServiceContainer();
    window.Hevno = { services: this.services };

    const hookManager = new HookManager();
    const remoteProxy = new RemoteHookProxy();
    const globalHookRegistry = new GlobalHookRegistry();
    const manifestProvider = new ManifestProvider();
    
    hookManager.setDependencies(remoteProxy, globalHookRegistry);
    remoteProxy.setHookManager(hookManager);

    this.services.register('hookManager', hookManager, 'loader');
    this.services.register('remoteProxy', remoteProxy, 'loader');
    this.services.register('globalHookRegistry', globalHookRegistry, 'loader');
    this.services.register('manifestProvider', manifestProvider, 'loader');

    if (import.meta.env.DEV) {
      window.hevno = this.services;
    }
  }

  async load() {
    console.log("🚀 Hevno Frontend Loader starting...");
    const remoteProxy = this.services.get('remoteProxy');
    const globalHookRegistry = this.services.get('globalHookRegistry');
    const manifestProvider = this.services.get('manifestProvider');

    try {
      console.log("[Loader] 正在获取后端钩子清单...");
      const hooksResponse = await fetch('/api/system/hooks/manifest');
      if (!hooksResponse.ok) {
          throw new Error(`无法获取后端钩子清单: ${hooksResponse.statusText}`);
      }
      const backendHooksData = await hooksResponse.json();
      globalHookRegistry.setBackendHooks(backendHooksData.hooks);
      
      remoteProxy.connect();

      console.log("[Loader] 正在获取插件清单...");
      const manifestResponse = await fetch('/api/plugins/manifest');
      if (!manifestResponse.ok) {
        throw new Error(`无法获取插件清单: ${manifestResponse.statusText}`);
      }
      let allManifests = await manifestResponse.json();
      
      const frontendPlugins = allManifests
        .filter(m => m.frontend && m.frontend.entryPoint)
        .sort((a, b) => (a.frontend?.priority || 0) - (b.frontend?.priority || 0));

      console.log(`发现 ${frontendPlugins.length} 个前端插件待加载:`, frontendPlugins.map(p => p.id));


      for (const manifest of frontendPlugins) {
        manifestProvider.addManifest(manifest);
        try {
          let entryPointUrl = '';

          if (import.meta.env.DEV) {
            const srcEntryPoint = manifest.frontend.srcEntryPoint || `src/main.${manifest.id.includes('goliath') ? 'jsx' : 'js'}`;
            entryPointUrl = `/plugins/${manifest.id}/${srcEntryPoint}`;
            console.log(`[DEV MODE] Loading source for ${manifest.id}: ${entryPointUrl}`);
          } else {
            entryPointUrl = `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;
          }
          
          const pluginModule = await import(entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
            console.log(`-> 正在注册插件: ${manifest.id} (priority: ${manifest.frontend?.priority || 0})`);
            await Promise.resolve(pluginModule.registerPlugin(this.services));
          }
        } catch (e) {
          console.error(`加载或注册插件 ${manifest.id} 失败:`, e);
        }
      }
      // ===============================================================

      console.log("[Loader] 所有插件已加载。正在与后端同步前端钩子...");
      remoteProxy.syncFrontendHooks();

    } catch (e) {
      console.error("致命错误: 无法初始化插件。", e);
      document.body.innerHTML = `<div style="color: red; padding: 2rem;">错误: 无法从后端加载插件清单。后端服务器是否正在运行？</div>`;
      return;
    }

    console.log("✅ 同步完成。正在将控制权移交给应用插件...");
    await this.services.get('hookManager').trigger('loader.ready');
  }
}

const loader = new FrontendLoader();
loader.load();