// File: packages/kernel/src/types.ts

import React from 'react';

/**
 * Kernel 内部使用的插件清单结构，反映了新的 manifest.json 格式。
 * 它清晰地区分了后端和前端的配置。
 */
export interface PluginManifest {
  id: string;
  name: string;
  source?: string; // 从何处加载，主要由后端使用

  backend?: {
    priority?: number;
    [key: string]: any;
  };
  
  frontend?: {
    entryPoint: string;
    priority?: number;
    contributions?: {
      views?: Record<string, { id: string, component: string }[]>;
      [key: string]: any;
    };
  };
}


/**
 * Kernel 传递给插件生命周期钩子的上下文对象
 */
export interface PluginContext {
  registerComponent: (name: string, component: React.ComponentType<any>) => void;
  getManifest: () => PluginManifest;
}

/**
 * Kernel 内部使用的插件生命周期定义
 */
export interface PluginLifecycle {
  onLoad?: (context: PluginContext) => void | Promise<void>;
  onActivate?: (context: PluginContext) => void | Promise<void>;
  [key: string]: any;
}

/**
 * Kernel 内部对 PluginService 实现的接口
 */
export interface IPluginService {
    getPluginManifest(id: string): PluginManifest | undefined;
    getAllViewContributions(): Record<string, any[]>;
    getComponent(pluginId: string, componentName: string): React.ComponentType<any> | undefined;
    loadPlugins(): Promise<void>;
}