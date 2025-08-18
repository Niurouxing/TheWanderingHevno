// frontend/main.js

import { ServiceContainer } from './ServiceContainer.js';
import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';
import { GlobalHookRegistry } from './services/GlobalHookRegistry.js';
import { ContributionService } from './services/ContributionService.js';

class FrontendLoader {
  constructor() {
    this.services = new ServiceContainer();
    window.Hevno = { services: this.services };

    const hookManager = new HookManager();
    const remoteProxy = new RemoteHookProxy();
    const globalHookRegistry = new GlobalHookRegistry();
    const contributionService = new ContributionService();
    
    hookManager.setDependencies(remoteProxy, globalHookRegistry);
    remoteProxy.setHookManager(hookManager);

    this.services.register('hookManager', hookManager, 'loader');
    this.services.register('remoteProxy', remoteProxy, 'loader');
    this.services.register('globalHookRegistry', globalHookRegistry, 'loader');
    this.services.register('contributionService', contributionService, 'loader');

    if (import.meta.env.DEV) {
      window.hevno = this.services;
    }
  }

  async load() {
    console.log("🚀 Hevno Frontend Loader starting...");
    const remoteProxy = this.services.get('remoteProxy');
    const globalHookRegistry = this.services.get('globalHookRegistry');
    const contributionService = this.services.get('contributionService');

    // [修复] 在函数顶部声明 allManifests，使其在整个函数作用域内可用
    let allManifests = [];

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
      // [修复] 给已声明的 allManifests 变量赋值，而不是重新声明
      allManifests = await manifestResponse.json();
      
      contributionService.processManifests(allManifests);
      
      const frontendPlugins = allManifests
        .filter(m => m.frontend && m.frontend.entryPoint)
        .sort((a, b) => (a.frontend?.priority || 0) - (b.frontend?.priority || 0));

      console.log(`发现 ${frontendPlugins.length} 个前端插件待加载:`, frontendPlugins.map(p => p.id));

      for (const manifest of frontendPlugins) {
        try {
          let entryPointUrl = import.meta.env.DEV 
            ? `/plugins/${manifest.id}/${manifest.frontend.srcEntryPoint || `src/main.${manifest.id.includes('goliath') ? 'jsx' : 'js'}`}`
            : `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;

          const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            console.log(`-> 正在注册插件服务: ${manifest.id} (priority: ${manifest.frontend?.priority || 0})`);
            await Promise.resolve(pluginModule.registerPlugin(this.services));
          }
        } catch (e) {
          console.error(`加载或注册插件 ${manifest.id} 失败:`, e);
        }
      }

      console.log("[Loader] 所有插件服务已注册。正在与后端同步前端钩子...");
      remoteProxy.syncFrontendHooks();

    } catch (e) {
      console.error("致命错误: 无法初始化插件。", e);
      document.body.innerHTML = `<div style="color: red; padding: 2rem;">错误: 无法从后端加载插件清单。后端服务器是否正在运行？</div>`;
      return;
    }

    // [核心重构] 使用贡献点机制代替硬编码的 'loader.ready' 钩子来启动UI
    console.log("✅ 同步完成。正在寻找并初始化应用宿主 (frontend.host)...");
    
    const hostContributions = contributionService.getContributionsFor('frontend.host');

    if (hostContributions.length === 0) {
      document.body.innerHTML = `<div style="color: red; padding: 2rem;">致命错误: 未找到任何提供 'frontend.host' 贡献的应用宿主插件。</div>`;
      return;
    }

    if (hostContributions.length > 1) {
      console.warn(`[Loader] 发现 ${hostContributions.length} 个应用宿主插件。将使用第一个: '${hostContributions[0].pluginId}'`);
    }

    const hostContribution = hostContributions[0];
    // 现在这里的 allManifests 是可访问的
    const hostPluginManifest = allManifests.find(m => m.id === hostContribution.pluginId);

    if (!hostPluginManifest) {
       document.body.innerHTML = `<div style="color: red; padding: 2rem;">致命错误: 无法找到宿主插件 '${hostContribution.pluginId}' 的清单文件。</div>`;
       return;
    }

    try {
      const entryPointUrl = import.meta.env.DEV
        ? `/plugins/${hostPluginManifest.id}/${hostPluginManifest.frontend.srcEntryPoint}`
        : `/plugins/${hostPluginManifest.id}/${hostPluginManifest.frontend.entryPoint}`;
      
      const pluginModule = await import(/* @vite-ignore */ entryPointUrl);
      const initializerFn = pluginModule[hostContribution.initializerExportName];

      if (typeof initializerFn === 'function') {
        console.log(`[Loader] 正在将控制权移交给宿主插件 '${hostPluginManifest.id}'...`);
        await Promise.resolve(initializerFn(this.services));
      } else {
        throw new Error(`在插件 '${hostPluginManifest.id}' 中未找到导出的初始化函数 '${hostContribution.initializerExportName}'。`);
      }
    } catch (e) {
      console.error(`致命错误: 初始化宿主插件 '${hostPluginManifest.id}' 失败。`, e);
      document.body.innerHTML = `<div style="color: red; padding: 2rem;">错误: 初始化应用宿主失败。详情请查看控制台。</div>`;
    }
  }
}

const loader = new FrontendLoader();
loader.load();