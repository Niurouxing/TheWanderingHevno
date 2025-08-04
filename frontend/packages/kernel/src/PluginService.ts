// frontend/packages/kernel/src/PluginService.ts

import { HevnoGlobal } from './types';

export class PluginService {
  private manifests: any[] = [];

  constructor(private apiService: any /* APIService instance */) {}

  public async loadPlugins() {
    console.log('🔌 [Kernel] Loading plugins...');
    // 1. 从后端获取插件清单
    this.manifests = await this.apiService.get('/api/plugins/manifest');
    
    // 2. 筛选并排序前端插件
    const frontendPlugins = this.manifests
      .filter(p => p.config?.type === 'frontend')
      .sort((a, b) => (a.config.priority || 50) - (b.config.priority || 50));

    // 3. 按顺序动态加载插件入口脚本
    for (const plugin of frontendPlugins) {
      const entryPoint = plugin.config.entryPoint;
      if (!entryPoint) continue;
      
      console.log(`  -> Loading plugin: ${plugin.name} (from ${entryPoint})`);
      await this.loadScript(entryPoint);

      // 触发插件加载钩子
      (window as any).Hevno.services.hooks.trigger(`plugin:loaded`, plugin.name);
    }
  }

  private loadScript(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.type = 'module';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${url}`));
      document.body.appendChild(script);
    });
  }
}