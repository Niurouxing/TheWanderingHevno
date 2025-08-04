// frontend/packages/kernel/src/PluginService.ts

import React from 'react';
import { APIService } from './APIService';
import { HookSystem } from './HookSystem';
// [已更新] 从内核本地的 `types.ts` 文件导入新的类型定义
import { PluginLifecycle, PluginManifest, PluginContext, IPluginService } from './types';

/**
 * 一个内部接口，用于存储已加载和部分初始化的插件状态。
 * @internal
 */
interface LoadedPlugin {
  manifest: PluginManifest;
  lifecycle: PluginLifecycle;
  components: Map<string, React.ComponentType<any>>;
}

/**
 * PluginService 是前端内核的核心，负责管理所有前端插件的发现、
 * 加载、激活和生命周期。
 */
export class PluginService implements IPluginService {
  private manifests: PluginManifest[] = [];
  private loadedPlugins = new Map<string, LoadedPlugin>();

  constructor(
    private apiService: APIService, 
    private hooks: HookSystem
  ) {}

  /**
   * 根据插件ID获取其清单文件。
   */
  public getPluginManifest(id: string): PluginManifest | undefined {
    return this.manifests.find(m => m.id === id);
  }

  /**
   * [已更新] 聚合所有已加载插件的视图贡献。
   * 现在从 `manifest.frontend.contributions` 获取数据。
   */
  public getAllViewContributions(): Record<string, any[]> {
    const contributions: Record<string, any[]> = {};

    for (const [pluginId, plugin] of this.loadedPlugins.entries()) {
      // [!] 核心改动：从 `frontend` 对象中安全地访问贡献点
      const viewContribs = plugin.manifest.frontend?.contributions?.views;
      if (!viewContribs) continue;

      for (const contributionPoint in viewContribs) {
        if (!contributions[contributionPoint]) {
          contributions[contributionPoint] = [];
        }
        const enrichedContribs = viewContribs[contributionPoint].map(c => ({
          ...c,
          pluginId: pluginId,
        }));
        contributions[contributionPoint].push(...enrichedContribs);
      }
    }
    return contributions;
  }
  
  /**
   * 从指定插件获取一个已注册的React组件。
   */
  public getComponent(pluginId: string, componentName: string): React.ComponentType<any> | undefined {
    return this.loadedPlugins.get(pluginId)?.components.get(componentName);
  }

  /**
   * [已更新] 启动完整的插件加载和初始化流程。
   * 此方法现在使用新的、更健壮的逻辑来过滤和排序插件。
   */
  public async loadPlugins() {
    console.log('🔌 [Kernel] Starting plugin loading process...');

    // --- 阶段 0: 获取插件清单 ---
    try {
      this.manifests = await this.apiService.get<PluginManifest[]>('/api/plugins/manifest');
    } catch (error) {
        console.error('Fatal: Could not fetch plugin manifest from backend. Halting boot process.', error);
        this.hooks.trigger('system:fatal', { error: 'Failed to load plugin manifest.' });
        return;
    }
    
    // [!] 核心改动：过滤和排序逻辑更新
    const frontendPlugins = this.manifests
      // 只要插件定义了 `frontend.entryPoint`，就认为它是可加载的前端插件
      .filter(p => p.frontend?.entryPoint)
      // 优先级现在从 `frontend` 对象中获取
      .sort((a, b) => (a.frontend!.priority ?? 50) - (b.frontend!.priority ?? 50));

    // --- 阶段 1: 加载 (Load) ---
    console.log('  -> Phase 1: Loading all plugin scripts...');
    for (const manifest of frontendPlugins) {
      // [!] 核心改动：优先级和入口点从 `frontend` 对象获取
      const { entryPoint, priority } = manifest.frontend!;
      console.log(`     - Loading: ${manifest.id} (priority: ${priority})`);
      try {
        await this.loadModule(entryPoint);
        
        const lifecycle = (window as any).__HEVNO_PENDING_PLUGIN__ as PluginLifecycle;
        if (!lifecycle) {
          console.warn(`Plugin ${manifest.id} was loaded but did not export a lifecycle via definePlugin.`);
          continue;
        }
        delete (window as any).__HEVNO_PENDING_PLUGIN__;

        this.loadedPlugins.set(manifest.id, {
            manifest,
            lifecycle,
            components: new Map()
        });
      } catch (error) {
        console.error(`Failed to load script for plugin: ${manifest.id} from ${entryPoint}`, error);
      }
    }

    // --- 阶段 2: 安装 (Install / onLoad) ---
    console.log('  -> Phase 2: Executing "onLoad" lifecycle hooks...');
    for (const [id, plugin] of this.loadedPlugins.entries()) {
      if (plugin.lifecycle.onLoad) {
        const context: PluginContext = {
          registerComponent: (name, component) => {
            console.log(`[Plugin: ${id}] registered component: ${name}`);
            plugin.components.set(name, component);
          },
          getManifest: () => plugin.manifest,
        };
        await Promise.resolve(plugin.lifecycle.onLoad(context));
      }
    }
    
    // --- 阶段 3: 激活 (Activate / onActivate) ---
    console.log('  -> Phase 3: Executing "onActivate" lifecycle hooks...');
    for (const [, plugin] of this.loadedPlugins.entries()) {
        if (plugin.lifecycle.onActivate) {
            const context: PluginContext = {
                registerComponent: (name, component) => plugin.components.set(name, component),
                getManifest: () => plugin.manifest,
            };
            await Promise.resolve(plugin.lifecycle.onActivate(context));
        }
    }

    console.log('✅ [Kernel] All plugins loaded and activated.');
    this.hooks.trigger('plugins:ready');
  }

  /**
   * 使用现代的动态 `import()` 语法来加载一个JS模块。
   */
  private loadModule(url: string): Promise<any> {
    return import(/* @vite-ignore */ url);
  }
}