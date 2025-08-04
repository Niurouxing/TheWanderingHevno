// frontend/packages/frontend-sdk/src/types.ts

import React from 'react';

// --- 核心服务接口 ---
// 这些接口定义了内核服务的公共API，供插件类型安全地使用。

export interface ServiceRegistry {
  register<T>(name: string, instance: T): void;
  resolve<T>(name: string): T;
}

export interface ServiceBus {
  on(eventName: string, handler: (payload?: any) => void): () => void;
  off(eventName:string, handler: (payload?: any) => void): void;
  emit(eventName: string, payload?: any): void;
}

export interface HookSystem {
  addImplementation(hookName: string, handler: (...args: any[]) => any): void;
  trigger(hookName: string, ...args: any[]): Promise<void>;
  filter<T>(hookName: string, initialValue: T, ...args: any[]): Promise<T>;
}

export interface APIService {
  get<T>(endpoint: string): Promise<T>;
  post<T>(endpoint: string, body: any): Promise<T>;
  put<T>(endpoint: string, body: any): Promise<T>;
  delete<T>(endpoint: string): Promise<T>;
  // ... 其他方法
}

// 注意: PluginService的接口定义是给插件消费的，
// 所以只暴露插件需要的方法。
export interface PluginService {
    getPluginManifest(id: string): PluginManifest | undefined;
    getAllViewContributions(): Record<string, any[]>;
    getComponent(pluginId: string, componentName: string): React.ComponentType<any> | undefined;
}


// --- 全局命名空间 ---

export interface HevnoGlobal {
  services: {
    registry: ServiceRegistry;
    bus: ServiceBus;
    hooks: HookSystem;
    api: APIService;
    plugins: PluginService; // 注意这里用的是接口
  };
}


// --- 插件系统核心类型 ---

/**
 * 描述了从 hevno.json/后端API 获取的单个插件的清单结构
 */
export interface PluginManifest {
  id: string; // 插件ID，来自 hevno.json 的键名
  source: string;
  type: 'frontend' | 'backend';
  config: {
    entryPoint: string;
    priority: number;
    contributions?: {
      views?: Record<string, { id: string, component: string }[]>;
      commands?: { id: string, title: string, category?: string }[];
      // ... 其他贡献点
    };
  };
  // ... 其他元数据，如 name, version, description
}


/**
 * 【关键】插件上下文对象
 * 这个对象在调用插件生命周期钩子时被注入，
 * 为插件提供了一个安全的、与自身绑定的API集合。
 */
export interface PluginContext {
  /**
   * 注册一个属于该插件的React组件。
   * @param name 组件的唯一名称（在插件内部）
   * @param component React组件本身
   */
  registerComponent: (name: string, component: React.ComponentType<any>) => void;
  
  /**
   * 获取当前插件的清单信息
   */
  getManifest: () => PluginManifest;
}

/**
 * 定义了一个前端插件必须实现的生命周期钩子。
 * 插件通过在入口文件中调用 `definePlugin(lifecycle)` 来导出这些钩子。
 */
export interface PluginLifecycle {
  /**
   * 在插件脚本加载后、但任何UI渲染之前立即调用。
   * 这是注册服务、组件和命令处理程序的最佳时机。
   * @param context 一个与当前插件绑定的上下文对象。
   */
  onLoad?: (context: PluginContext) => void | Promise<void>;

  /**
   * 在所有插件的 `onLoad` 都完成后调用。
   * 适用于需要与其他插件的服务进行交互的初始化逻辑。
   * @param context 一个与当前插件绑定的上下文对象。
   */
  onActivate?: (context: PluginContext) => void | Promise<void>;
  
  /**
   * （未来）在所有服务都准备好后调用。
   */
  onServicesReady?: (context: PluginContext) => void | Promise<void>;
  
  /**
   * （未来）在插件被停用时调用。
   */
  onDeactivate?: () => void | Promise<void>;
}