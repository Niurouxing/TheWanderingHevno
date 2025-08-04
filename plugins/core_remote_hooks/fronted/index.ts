import { definePlugin, services, PluginContext } from '@hevno/frontend-sdk';
import ConnectionStatus from './components/ConnectionStatus';

/**
 * RemoteHookService 负责管理与后端 WebSocket 的单一持久连接，
 * 并作为前后端事件系统的桥梁。
 */
class RemoteHookService {
    private ws: WebSocket | null = null;
    private readonly wsUrl: string;
    private reconnectInterval: number = 5000; // 5秒后重连

    constructor() {
        // 从环境变量或配置中获取URL，提供一个默认值
        const host = import.meta.env.VITE_API_HOST || window.location.host;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${protocol}//${host}/ws/hooks`;
    }

    /**
     * 启动并管理 WebSocket 连接。
     */
    public connect(): void {
        console.log(`[RemoteHooks] Attempting to connect to ${this.wsUrl}...`);
        
        // 如果已有连接，先关闭
        if (this.ws) {
            this.ws.close();
        }

        this.ws = new WebSocket(this.wsUrl);
        this.registerEventListeners();
    }

    /**
     * 注册 WebSocket 的核心事件监听器。
     */
    private registerEventListeners(): void {
        if (!this.ws) return;

        this.ws.onopen = () => {
            console.log('🔗 [RemoteHooks] WebSocket connection established.');
            // 在前端事件总线上广播连接成功事件
            services.bus.emit('websocket:status_changed', { status: 'connected' });
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                // 校验消息格式
                if (message && typeof message.hook_name === 'string') {
                    console.log(`⬇️ [RemoteHooks] Received hook: ${message.hook_name}`, message.data || {});
                    // 在前端事件总线上将后端事件重新广播出去
                    // 这样，任何前端插件都可以通过 services.bus.on(...) 来监听后端事件
                    services.bus.emit(message.hook_name, message.data);
                } else {
                     console.warn('[RemoteHooks] Received an invalid message format from server:', event.data);
                }
            } catch (e) {
                console.error('[RemoteHooks] Failed to parse message from server:', e);
            }
        };

        this.ws.onclose = (event) => {
            console.log(`🔌 [RemoteHooks] WebSocket connection closed. Code: ${event.code}. Reconnecting in ${this.reconnectInterval / 1000}s...`);
            // 广播连接断开事件
            services.bus.emit('websocket:status_changed', { status: 'disconnected' });
            
            // 简单的自动重连逻辑
            setTimeout(() => this.connect(), this.reconnectInterval);
        };

        this.ws.onerror = (error) => {
            console.error('[RemoteHooks] WebSocket error:', error);
            // 错误事件通常会紧随着关闭事件，所以重连逻辑放在 onclose 中处理
        };
    }

    /**
     * 向后端发送一个钩子事件。这是前端触发后端逻辑的主要方式。
     * @param hook_name 要在后端触发的钩子名称。
     * @param data 附加的数据负载。
     */
    public trigger(hook_name: string, data: any = {}): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            const payload = JSON.stringify({ hook_name, data });
            console.log(`⬆️ [RemoteHooks] Triggering remote hook: ${hook_name}`, data);
            this.ws.send(payload);
        } else {
            console.error(`[RemoteHooks] Cannot trigger hook "${hook_name}". WebSocket is not open (state: ${this.ws?.readyState}).`);
        }
    }
}


// --- 插件定义 ---

export default definePlugin({
    /**
     * onLoad 钩子：在插件脚本加载后立即执行。
     * 这是注册静态资源（如组件）的最佳时机。
     */
    onLoad: (context: PluginContext) => {
        // 注册 ConnectionStatus UI 组件，以便 core-layout 插件可以渲染它。
        context.registerComponent('ConnectionStatus', ConnectionStatus);
    },

    /**
     * onActivate 钩子：在所有插件的 onLoad 都完成后执行。
     * 这是初始化服务、建立网络连接等动态操作的安全时机。
     */
    onActivate: () => {
        // 1. 创建 RemoteHookService 的单例实例。
        const remoteHookService = new RemoteHookService();
        
        // 2. 将服务实例注册到内核的服务注册表中，
        //    以便其他插件可以通过 useService('remoteHookService') 来获取和使用它。
        services.registry.register('remoteHookService', remoteHookService);
        
        // 3. 启动 WebSocket 连接。
        remoteHookService.connect();
    }
});