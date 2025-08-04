// frontend/packages/kernel/src/PluginService.ts

import React from 'react';
import { APIService } from './APIService';
import { HookSystem } from './HookSystem';
import { PluginLifecycle, PluginManifest, PluginContext, PluginService as IPluginService } from '@hevno/frontend-sdk';

/**
 * 内核内部用来追踪已加载插件状态的接口。
 */
interface LoadedPlugin {
  manifest: PluginManifest;
  lifecycle: PluginLifecycle;
  components: Map<string, React.ComponentType<any>>;
}

/**
 * PluginService 负责管理整个前端插件生态系统。
 */
export class PluginService implements IPluginService {
  private manifests: PluginManifest[] = [];
  private loadedPlugins = new Map<string, LoadedPlugin>();

  constructor(private apiService: APIService, private hooks: HookSystem) {}

  public getPluginManifest(id: string): PluginManifest | undefined {
    return this.manifests.find(m => m.id === id);
  }

  public getAllViewContributions(): Record<string, any[]> {
    const contributions: Record<string, any[]> = {};
    for (const [pluginId, plugin] of this.loadedPlugins.entries()) {
      const viewContribs = plugin.manifest.config.contributions?.views;
      if (!viewContribs) continue;

      for (const contributionPoint in viewContribs) {
        if (!contributions[contributionPoint]) {
          contributions[contributionPoint] = [];
        }
        // 注入插件ID，以便Layout服务后续能找到正确的组件
        const enrichedContribs = viewContribs[contributionPoint].map(c => ({
          ...c,
          pluginId: pluginId 
        }));
        contributions[contributionPoint].push(...enrichedContribs);
      }
    }
    return contributions;
  }
  
  public getComponent(pluginId: string, componentName: string): React.ComponentType<any> | undefined {
    return this.loadedPlugins.get(pluginId)?.components.get(componentName);
  }

  /**
   * 启动插件加载的主流程。
   */
  public async loadPlugins() {
    console.log('🔌 [Kernel] Starting plugin loading process...');

    // 阶段 0: 获取插件清单
    // 后端返回一个对象 { "plugin-id": { manifest... } }
    const manifestObject = await this.apiService.get<Record<string, Omit<PluginManifest, 'id'>>>('/api/plugins/manifest');
    
    this.manifests = Object.entries(manifestObject).map(([id, manifest]) => ({
        id,
        ...manifest,
    }));
    
    const frontendPlugins = this.manifests
      .filter(p => p.type === 'frontend' && p.config?.entryPoint)
      .sort((a, b) => (a.config.priority ?? 50) - (b.config.priority ?? 50));

    // 阶段 1: 加载所有插件脚本
    // 这个阶段只执行脚本，不调用任何生命周期钩子。
    console.log('  -> Phase 1: Loading all plugin scripts...');
    for (const manifest of frontendPlugins) {
      console.log(`     - Loading: ${manifest.id} (priority: ${manifest.config.priority})`);
      try {
        await this.loadScript(manifest.config.entryPoint);
        // 脚本执行后，`definePlugin` 会把 lifecycle 放到全局临时变量上
        const lifecycle = (window as any).__HEVNO_PENDING_PLUGIN__ as PluginLifecycle;
        delete (window as any).__HEVNO_PENDING_PLUGIN__;

        if (!lifecycle) {
          console.warn(`Plugin ${manifest.id} loaded but did not export a lifecycle via definePlugin.`);
          continue;
        }

        this.loadedPlugins.set(manifest.id, {
            manifest,
            lifecycle,
            components: new Map() // 初始化空的组件注册表
        });
      } catch (error) {
        console.error(`Failed to load script for plugin: ${manifest.id}`, error);
      }
    }

    // 阶段 2: 执行所有插件的 `onLoad` 钩子
    // 这是注册组件和服务的时机。
    console.log('  -> Phase 2: Executing "onLoad" lifecycle hooks...');
    for (const [id, plugin] of this.loadedPlugins.entries()) {
      if (plugin.lifecycle.onLoad) {
        // 【关键】为每个插件创建独立的上下文
        const context: PluginContext = {
          registerComponent: (name, component) => {
            plugin.components.set(name, component);
          },
          getManifest: () => plugin.manifest,
        };
        await Promise.resolve(plugin.lifecycle.onLoad(context));
      }
    }
    
    // 阶段 3: 执行所有插件的 `onActivate` 钩子
    // 这个阶段可以安全地使用其他插件注册的服务。
    console.log('  -> Phase 3: Executing "onActivate" lifecycle hooks...');
    for (const [id, plugin] of this.loadedPlugins.entries()) {
        if (plugin.lifecycle.onActivate) {
            const context: PluginContext = {
                registerComponent: (name, component) => plugin.components.set(name, component),
                getManifest: () => plugin.manifest,
            };
            await Promise.resolve(plugin.lifecycle.onActivate(context));
        }
    }

    console.log('✅ [Kernel] All plugins loaded and activated.');
    // 触发 `plugins:ready` 钩子，通知应用可以开始渲染UI了。
    this.hooks.trigger('plugins:ready');
  }

  /**
   * 动态加载一个JS模块脚本。
   */
  private loadScript(url: string): Promise<void> {
    // 【关键】这里的 `url` 是从 manifest.json 的 entryPoint 字段来的。
    // 例如: /plugins/core-layout/dist/index.js
    
    // 如果我们的API基础URL是 http://localhost:8000，那么这个相对路径会自动解析为：
    // http://localhost:8000/plugins/core-layout/dist/index.js
    // 这恰好命中了后端的新端点 `GET /plugins/{plugin_id}/{resource_path}`
    
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      
      // Vite dev server 可能会有不同的基础路径，需要处理
      // 生产环境中，通常我们不设置 base，所以相对路径是正确的
      const baseUrl = import.meta.env.BASE_URL || '/';
      const finalUrl = new URL(url.startsWith('/') ? url.substring(1) : url, baseUrl).href;
      
      // 在生产环境中，我们通常直接使用相对路径。
      // 为简单起见，我们假设 VITE_API_BASE_URL 只用于 API 调用，不用于静态资源。
      // script.src = url; // 保持这个即可
      
      // 一个更健壮的方式是，区分开发和生产
      const isDev = import.meta.env.DEV;
      let scriptSrc = url;

      if (isDev) {
        // 在开发模式下，Vite会处理插件的HMR，通常不需要特殊处理。
        // 但如果后端也在开发模式下服务插件，我们需要拼接URL。
        // Vite代理可以很好地解决这个问题。我们暂时假设Vite处理了它。
      }

      script.src = scriptSrc;
      script.type = 'module';
      script.async = true;
      script.onload = () => {
        script.remove();
        resolve();
      };
      script.onerror = () => {
        script.remove();
        reject(new Error(`Failed to load script: ${scriptSrc}`));
      };
      document.head.appendChild(script);
    });
  }
}