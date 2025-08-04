/**
 * 一个简单的前端事件总线 (发布/订阅模式)。
 * 允许插件之间进行解耦通信。
 */
export class HookManager {
  constructor() {
    this.hooks = new Map();
  }

  /**
   * 注册一个钩子实现。
   * @param {string} hookName - 钩子的名称。
   * @param {Function} implementation - 要执行的函数。
   */
  addImplementation(hookName, implementation) {
    if (!this.hooks.has(hookName)) {
      this.hooks.set(hookName, []);
    }
    this.hooks.get(hookName).push(implementation);
  }

  /**
   * 触发一个“通知型”钩子。
   * 并发执行所有实现，不关心返回值。
   * @param {string} hookName - 钩子名称。
   * @param {object} data - 传递给钩子实现的数据。
   */
  async trigger(hookName, data = {}) {
    const implementations = this.hooks.get(hookName) || [];
    const tasks = implementations.map(impl => Promise.resolve(impl(data)));
    await Promise.all(tasks);
  }

  /**
   * 触发一个“过滤型”钩子。
   * 按注册顺序链式执行，后一个实现接收前一个的返回值。
   * @param {string} hookName - 钩子名称。
   * @param {*} initialData - 初始数据。
   * @param {object} extraData - 传递给每个实现的额外上下文数据。
   * @returns {*} 经过所有实现处理后的最终数据。
   */
  async filter(hookName, initialData, extraData = {}) {
    const implementations = this.hooks.get(hookName) || [];
    let currentData = initialData;
    for (const impl of implementations) {
      currentData = await Promise.resolve(impl(currentData, extraData));
    }
    return currentData;
  }
}