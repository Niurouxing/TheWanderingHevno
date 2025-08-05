// frontend/services/GlobalHookRegistry.js

/**
 * 一个单例服务，用于存储和查询全域钩子路由表。
 * 它持有在前端和后端实现的所有钩子的完整清单。
 */
export class GlobalHookRegistry {
  constructor() {
    /** @type {Set<string>} */
    this.backendHooks = new Set();
    /** @type {Set<string>} */
    this.frontendHooks = new Set();
  }

  /**
   * 填充已知的后端钩子集合。在启动时调用。
   * @param {string[]} hooks - 来自后端的钩子名称数组。
   */
  setBackendHooks(hooks) {
    this.backendHooks = new Set(hooks);
    console.log(`[GlobalRegistry] 已注册 ${this.backendHooks.size} 个后端钩子。`);
  }

  /**
   * 将一个前端实现的钩子添加到注册表。
   * 由本地 HookManager 在每次添加实现时调用。
   * @param {string} hookName 
   */
  addFrontendHook(hookName) {
    if (!this.frontendHooks.has(hookName)) {
        this.frontendHooks.add(hookName);
    }
  }

  /**
   * 检查一个钩子是否有本地（前端）实现。
   * @param {string} hookName 
   * @returns {boolean}
   */
  isLocalHook(hookName) {
    return this.frontendHooks.has(hookName);
  }

  /**
   * 检查一个钩子是否有远程（后端）实现。
   * @param {string} hookName 
   * @returns {boolean}
   */
  isRemoteHook(hookName) {
    return this.backendHooks.has(hookName);
  }

  /**
   * 获取所有已知的前端钩子名称列表。
   * 用于与后端同步。
   * @returns {string[]}
   */
  getFrontendHooks() {
    return Array.from(this.frontendHooks);
  }
}