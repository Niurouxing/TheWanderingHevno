// frontend/packages/kernel/src/HookSystem.ts
type HookHandler = (...args: any[]) => any | Promise<any>;

export class HookSystem {
  private hooks = new Map<string, Set<HookHandler>>();

  public addImplementation(hookName: string, handler: HookHandler): void {
    if (!this.hooks.has(hookName)) {
      this.hooks.set(hookName, new Set());
    }
    this.hooks.get(hookName)!.add(handler);
  }

  // “通知型”钩子，并发执行，不关心返回值
  public async trigger(hookName: string, ...args: any[]): Promise<void> {
    const handlers = this.hooks.get(hookName);
    if (!handlers) return;

    const promises = Array.from(handlers).map(handler => Promise.resolve(handler(...args)));
    await Promise.all(promises);
  }

  // “过滤型”钩子，串行链式执行
  public async filter<T>(hookName: string, initialValue: T, ...args: any[]): Promise<T> {
    const handlers = this.hooks.get(hookName);
    if (!handlers) return initialValue;

    let currentValue = initialValue;
    for (const handler of Array.from(handlers)) {
      currentValue = await Promise.resolve(handler(currentValue, ...args));
    }
    return currentValue;
  }
}