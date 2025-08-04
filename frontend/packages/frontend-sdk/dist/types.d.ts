import { default as React } from 'react';

/**
 * 代表一个独立的交互会话或“游戏存档”。
 * 对应后端 /api/sandboxes 端点的数据。
 */
export interface Sandbox {
    id: string;
    name: string;
    head_snapshot_id: string;
    created_at: string;
}
/**
 * 代表世界在某个特定时刻的完整、不可变的状态。
 * 对应后端 StateSnapshot 模型。
 */
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
/**
 * 记忆系统中的一个记忆流。
 */
export interface MemoryStream {
    config: Record<string, any>;
    entries: MemoryEntry[];
    synthesis_trigger_counter: number;
}
/**
 * 记忆流中的一个单独的记忆条目。
 */
export interface MemoryEntry {
    id: string;
    sequence_id: number;
    level: string;
    tags: string[];
    content: string;
    created_at: string;
}
/**
 * 图的集合，其中 `main` 是主入口图。
 */
export interface GraphCollection {
    [graphName: string]: GraphDefinition;
}
/**
 * 单个图的定义。
 */
export interface GraphDefinition {
    nodes: GenericNode[];
    metadata?: Record<string, any>;
}
/**
 * 图中的一个基本执行单元。
 */
export interface GenericNode {
    id: string;
    run: RuntimeInstruction[];
    depends_on?: string[];
    metadata?: Record<string, any>;
}
/**
 * 定义节点行为的原子指令。
 */
export interface RuntimeInstruction {
    runtime: string;
    config: Record<string, any>;
}
/**
 * 描述了从 /api/plugins/manifest 获取的单个插件的清单结构。
 * 这是插件的“身份证”。
 */
export interface PluginManifest {
    id: string;
    source: string;
    type: 'frontend' | 'backend';
    config: {
        entryPoint: string;
        priority: number;
        contributions?: {
            views?: Record<string, {
                id: string;
                component: string;
            }[]>;
            commands?: {
                id: string;
                title: string;
                category?: string;
            }[];
            themes?: {
                id: string;
                label: string;
                path: string;
            }[];
            settings?: {
                id: string;
                type: string;
                label: string;
                default: any;
            }[];
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
     * @param name 组件的唯一名称（在插件内部）。
     * @param component React 组件本身。
     */
    registerComponent: (name: string, component: React.ComponentType<any>) => void;
    /**
     * 获取当前插件自己的清单(Manifest)信息。
     */
    getManifest: () => PluginManifest;
}
/**
 * 定义了一个前端插件必须实现的生命周期钩子。
 * 插件通过在入口文件中调用 `definePlugin(lifecycle)` 来向内核注册自己。
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
     * (未来) 在所有核心服务都准备好后调用。
     */
    onServicesReady?: (context: PluginContext) => void | Promise<void>;
    /**
     * (未来) 在插件被停用时调用，用于清理资源。
     */
    onDeactivate?: () => void | Promise<void>;
}
export interface ServiceRegistry {
    register<T>(name: string, instance: T): void;
    resolve<T>(name: string): T;
}
export interface ServiceBus {
    /**
     * 订阅一个事件。
     * @returns 一个用于取消订阅的函数。
     */
    on(eventName: string, handler: (payload?: any) => void): () => void;
    off(eventName: string, handler: (payload?: any) => void): void;
    emit(eventName: string, payload?: any): void;
}
export interface HookSystem {
    addImplementation(hookName: string, handler: (...args: any[]) => any): void;
    /** 并发执行所有实现，不关心返回值 */
    trigger(hookName: string, ...args: any[]): Promise<void>;
    /** 串行执行所有实现，将上一个的结果传递给下一个 */
    filter<T>(hookName: string, initialValue: T, ...args: any[]): Promise<T>;
}
export interface APIService {
    get<T>(endpoint: string): Promise<T>;
    post<T>(endpoint: string, body: any): Promise<T>;
    put<T>(endpoint: string, body: any): Promise<T>;
    delete<T>(endpoint: string): Promise<T>;
}
/**
 * 插件服务对其他插件暴露的公共接口。
 */
export interface PluginService {
    /** 获取指定插件的清单文件 */
    getPluginManifest(id: string): PluginManifest | undefined;
    /** 获取所有插件在所有贡献点的视图贡献 */
    getAllViewContributions(): Record<string, {
        id: string;
        component: string;
        pluginId: string;
    }[]>;
    /** 从指定插件获取已注册的组件 */
    getComponent(pluginId: string, componentName: string): React.ComponentType<any> | undefined;
}
/**
 * 定义了挂载在 `window.Hevno` 上的全局对象的结构。
 */
export interface HevnoGlobal {
    services: {
        registry: ServiceRegistry;
        bus: ServiceBus;
        hooks: HookSystem;
        api: APIService;
        plugins: PluginService;
    };
}
//# sourceMappingURL=types.d.ts.map