// frontend/HookManager.js

/**
 * 一个支持在前后端之间进行智能路由的事件总线。
 * 它查询一个全局注册表来决定将事件发送到何处。
 */
export class HookManager {
  constructor() {
    /** @type {Map<string, Function[]>} */
    this.hooks = new Map();
    
    /** @type {import('./RemoteHookProxy.js').RemoteHookProxy | null} */
    this.remoteProxy = null;
    /** @type {import('./services/GlobalHookRegistry.js').GlobalHookRegistry | null} */
    this.globalRegistry = null;
  }

  /**
   * 在实例化后注入依赖，以解决循环依赖问题。
   * @param {import('./RemoteHookProxy.js').RemoteHookProxy} remoteProxy
   * @param {import('./services/GlobalHookRegistry.js').GlobalHookRegistry} globalRegistry
   */
  setDependencies(remoteProxy, globalRegistry) {
    this.remoteProxy = remoteProxy;
    this.globalRegistry = globalRegistry;
  }
  
  /**
   * 注册一个钩子实现，并通知全局注册表。
   * @param {string} hookName - 钩子的名称。
   * @param {Function} implementation - 要执行的函数。
   */
  addImplementation(hookName, implementation) {
    if (!this.hooks.has(hookName)) {
      this.hooks.set(hookName, []);
    }
    this.hooks.get(hookName).push(implementation);

    // 任务 4.3: 通知全局注册表这个新的本地钩子
    if (this.globalRegistry) {
        this.globalRegistry.addFrontendHook(hookName);
    }
    
    console.log(`[HookManager] ADDED listener for hook: '${hookName}'`);
  }

  /**
   * 使用智能路由触发一个钩子。
   * 它会判断钩子应该在本地执行、远程执行，还是两者都执行。
   * 注意: 'filter' 类型的钩子目前仍被视为仅本地操作。
   * @param {string} hookName - 钩子的名称。
   * @param {object} data - 钩子的数据负载。
   */
  async trigger(hookName, data = {}) {
    if (!this.globalRegistry || !this.remoteProxy) {
        console.error(`[HookManager] 无法触发 '${hookName}'。核心服务未注入。`);
        return;
    }
    
    // 任务 4.3: 查询注册表
    const isLocal = this.globalRegistry.isLocalHook(hookName);
    const isRemote = this.globalRegistry.isRemoteHook(hookName);

    console.log(`[HookManager] TRIGGERING '${hookName}'. Local: ${isLocal}, Remote: ${isRemote}`);

    let wasHandled = false;

    // 任务 4.3: 路由到本地实现
    if (isLocal) {
      const implementations = this.hooks.get(hookName) || [];
      const tasks = implementations.map(impl => Promise.resolve(impl(data)));
      await Promise.all(tasks);
      wasHandled = true;
    }

    // 任务 4.3: 路由到远程（后端）实现
    if (isRemote) {
      this.remoteProxy.trigger(hookName, data);
      wasHandled = true;
    }
    
    // 任务 4.3: 如果在任何地方都未找到处理程序，则发出警告
    if (!wasHandled) {
      console.warn(`[HookManager] 触发的钩子 '${hookName}' 在前端或后端都没有已知的实现。`);
    }
  }

  /**
   * 触发一个“过滤型”钩子 (保留用于本地功能)。
   * 此类型被假定为同步和本地的，不用于远程通信。
   * @param {string} hookName 
   * @param {*} initialData 
   * @param {object} extraData 
   * @returns {*}
   */
  async filter(hookName, initialData, extraData = {}) {
    const implementations = this.hooks.get(hookName) || [];
    let currentData = initialData;
    for (const impl of implementations) {
      currentData = await Promise.resolve(impl(currentData, extraData));
    }
    return currentData;
  }
  
  /**
   * 获取所有已注册的前端钩子名称。
   * @returns {string[]}
   */
  getAllHookNames() {
    return Array.from(this.hooks.keys());
  }

  /**
   * 移除一个已注册的钩子实现。
   * @param {string} hookName - 钩子的名称。
   * @param {Function} implementationToRemove - 要移除的函数实例。
   */
  removeImplementation(hookName, implementationToRemove) {
    const implementations = this.hooks.get(hookName);
    if (!implementations) {
        return;
    }
    const index = implementations.indexOf(implementationToRemove);
    if (index > -1) {
        implementations.splice(index, 1);
        console.log(`[HookManager] REMOVED listener for hook: '${hookName}'`);
    }
  }
}