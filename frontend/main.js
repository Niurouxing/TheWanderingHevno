
import { ServiceContainer } from './ServiceContainer.js';
import { HookManager } from './HookManager.js';
import { RemoteHookProxy } from './RemoteHookProxy.js';
import { ManifestProvider } from './ManifestProvider.js';
import { GlobalHookRegistry } from './services/GlobalHookRegistry.js';

/**
 * Hevno 前端加载器 (内核)。
 * 职责被严格限定为：
 * 1. 初始化并提供最底层的、无业务逻辑的服务。
 * 2. 完成与后端的钩子清单交换。
 * 3. 从后端获取插件清单，并按优先级加载它们。
 * 4. 触发一个 `loader.ready` 钩子，然后将控制权完全移交。
 */
class FrontendLoader {
  constructor() {
    this.services = new ServiceContainer();
    window.Hevno = { services: this.services };

    // 1. 实例化所有核心服务，不使用构造函数注入
    const hookManager = new HookManager();
    const remoteProxy = new RemoteHookProxy();
    const globalHookRegistry = new GlobalHookRegistry(); // 新服务
    const manifestProvider = new ManifestProvider();
    
    // 2. 使用 setter 方法连接依赖关系，以解决循环依赖
    hookManager.setDependencies(remoteProxy, globalHookRegistry);
    remoteProxy.setHookManager(hookManager);

    // 3. 将所有服务注册到容器中
    this.services.register('hookManager', hookManager, 'loader');
    this.services.register('remoteProxy', remoteProxy, 'loader');
    this.services.register('globalHookRegistry', globalHookRegistry, 'loader');
    this.services.register('manifestProvider', manifestProvider, 'loader');

    // 方便调试
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
      // 步骤 1: 获取后端钩子清单
      console.log("[Loader] 正在获取后端钩子清单...");
      const hooksResponse = await fetch('/api/system/hooks/manifest');
      if (!hooksResponse.ok) {
          throw new Error(`无法获取后端钩子清单: ${hooksResponse.statusText}`);
      }
      const backendHooksData = await hooksResponse.json();
      globalHookRegistry.setBackendHooks(backendHooksData.hooks);
      
      // 步骤 2: 建立 WebSocket 连接
      remoteProxy.connect();

      // 步骤 3: 获取并加载所有前端插件
      console.log("[Loader] 正在获取插件清单...");
      const manifestResponse = await fetch('/api/plugins/manifest');
      if (!manifestResponse.ok) {
        throw new Error(`无法获取插件清单: ${manifestResponse.statusText}`);
      }
      let allManifests = await manifestResponse.json();
      
      const frontendPlugins = allManifests
        .filter(m => m.frontend && m.frontend.entryPoint)
        // ++ 核心修改：统一为升序排序 (数字小的先加载)
        .sort((a, b) => (a.frontend?.priority || 0) - (b.frontend?.priority || 0));

      console.log(`发现 ${frontendPlugins.length} 个前端插件待加载:`, frontendPlugins.map(p => p.id));

      // 依次加载并注册所有插件
      // 这将调用 `HookManager.addImplementation`，从而填充前端钩子注册表
      for (const manifest of frontendPlugins) {
        manifestProvider.addManifest(manifest);
        for (const manifest of frontendPlugins) {
        manifestProvider.addManifest(manifest);
        try {
          let entryPointUrl = '';

          if (import.meta.env.DEV) {
            // ===============================================================
            // 关键变更: 调整开发模式的路径构造
            // ===============================================================
            const srcEntryPoint = manifest.frontend.srcEntryPoint || `src/main.${manifest.id.includes('goliath') ? 'jsx' : 'js'}`; // 简单的后缀判断

            // 构造一个相对于项目根目录的绝对路径，并以 `/` 开头。
            // Vite Dev Server 会将这个路径视为从项目根目录开始寻找文件。
            // 例如: `/plugins/core_goliath/src/main.jsx`
            entryPointUrl = `/plugins/${manifest.id}/${srcEntryPoint}`;
            
            console.log(`[DEV MODE] Loading source for ${manifest.id}: ${entryPointUrl}`);

          } else {
            // 生产模式路径保持不变
            entryPointUrl = `/plugins/${manifest.id}/${manifest.frontend.entryPoint}`;
          }
          
          // 移除 `@vite-ignore`，让 Vite 处理这个动态导入
          const pluginModule = await import(entryPointUrl);
          
          if (pluginModule.registerPlugin) {
            console.log(`-> 正在注册插件: ${manifest.id} (priority: ${manifest.frontend?.priority || 0})`);
            await Promise.resolve(pluginModule.registerPlugin(this.services));
          }
        } catch (e) {
          console.error(`加载或注册插件 ${manifest.id} 失败:`, e);
        }
      }
        }

      // 【关键修复】步骤 4: 在所有插件加载后，与后端同步完整的前端钩子列表
      console.log("[Loader] 所有插件已加载。正在与后端同步前端钩子...");
      remoteProxy.syncFrontendHooks();

    } catch (e) {
      console.error("致命错误: 无法初始化插件。", e);
      document.body.innerHTML = `<div style="color: red; padding: 2rem;">错误: 无法从后端加载插件清单。后端服务器是否正在运行？</div>`;
      return;
    }

    // 内核工作结束！触发最终钩子，移交控制权。
    console.log("✅ 同步完成。正在将控制权移交给应用插件...");
    await this.services.get('hookManager').trigger('loader.ready');
  }
}

// 启动加载器
const loader = new FrontendLoader();
loader.load();