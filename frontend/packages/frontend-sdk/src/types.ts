// File: packages/frontend-sdk/src/types.ts

import React from 'react';


// 1. 后端 API 数据模型 (Models from Backend API)
//    这些类型精确匹配后端 REST API 返回的 JSON 结构。



export interface Sandbox {
  id: string;
  name: string;
  head_snapshot_id: string;
  created_at: string;
}

export interface StateSnapshot {
  id: string;
  sandbox_id: string;
  graph_collection: GraphCollection;
  world_state: Record<string, any> & {
    memoria?: Record<string, MemoryStream>;
  };
  created_at: string;
  parent_snapshot_id: string | null;
  triggering_input: Record<string, any>;
  run_output: Record<string, any> | null;
}

export interface MemoryStream {
  config: Record<string, any>;
  entries: MemoryEntry[];
  synthesis_trigger_counter: number;
}

export interface MemoryEntry {
  id: string;
  sequence_id: number;
  level: string;
  tags: string[];
  content: string;
  created_at: string;
}

export interface GraphCollection {
  [graphName: string]: GraphDefinition;
}

export interface GraphDefinition {
  nodes: GenericNode[];
  metadata?: Record<string, any>;
}

export interface GenericNode {
  id: string;
  run: RuntimeInstruction[];
  depends_on?: string[];
  metadata?: Record<string, any>;
}

export interface RuntimeInstruction {
  runtime: string;
  config: Record<string, any>;
}



// 2. 插件系统核心类型 (Plugin System Core Types)
//    定义了插件本身的结构和生命周期。


export interface PluginManifest {
  id: string;
  name: string;
  version?: string;
  description?: string;
  author?: string;

  // 后端特定的配置
  backend?: {
    priority?: number;
    [key: string]: any;
  };
  
  // 前端特定的配置
  frontend?: {
    entryPoint: string;
    priority?: number;
    contributions?: {
      views?: Record<string, { id: string, component: string }[]>;
      commands?: { id: string, title: string, category?: string }[];
      themes?: { id: string, label: string, path: string }[];
      settings?: { id: string, type: string, label: string, default: any }[];
      [key: string]: any;
    };
  };
}

/**
 * 插件上下文对象。
 * 这个对象在调用插件生命周期钩子时被内核注入，
 * 为插件提供了一个安全的、与自身绑定的 API 集合。
 */
export interface PluginContext {
  /**
   * 注册一个属于该插件的 React 组件，以便其他插件（如 core-layout）
   * 可以通过贡献点发现并渲染它。
   */
  registerComponent: (name: string, component: React.ComponentType<any>) => void;

  /**
   * 获取当前插件自己的清单(Manifest)信息。
   */
  getManifest: () => PluginManifest;
}

/**
 * 定义了一个前端插件必须实现的生命周期钩子。
 */
export interface PluginLifecycle {
  onLoad?: (context: PluginContext) => void | Promise<void>;
  onActivate?: (context: PluginContext) => void | Promise<void>;
  onServicesReady?: (context: PluginContext) => void | Promise<void>;
  onDeactivate?: () => void | Promise<void>;
}



// 3. 核心服务接口 (Core Service Interfaces)


export interface ServiceRegistry {
  register<T>(name: string, instance: T): void;
  resolve<T>(name: string): T;
}

export interface ServiceBus {
  on(eventName: string, handler: (payload?: any) => void): () => void;
  off(eventName: string, handler: (payload?: any) => void): void;
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
}

export interface PluginService {
  getPluginManifest(id: string): PluginManifest | undefined;
  getAllViewContributions(): Record<string, { id: string, component: string, pluginId: string }[]>;
  getComponent(pluginId: string, componentName: string): React.ComponentType<any> | undefined;
}



// 4. 全局命名空间 (Global Namespace)


export interface HevnoGlobal {
  services: {
    registry: ServiceRegistry;
    bus: ServiceBus;
    hooks: HookSystem;
    api: APIService;
    plugins: PluginService;
  };
}