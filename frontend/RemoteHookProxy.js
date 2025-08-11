// ./frontend/RemoteHookProxy.js

/**
 * 负责管理与后端 WebSocket 的连接，并作为前后端钩子系统的桥梁。
 * 它在连接建立后，向后端同步前端的钩子清单。
 */
export class RemoteHookProxy {
  constructor() {
    /** @type {import('./HookManager.js').HookManager | null} */
    this.localHookManager = null;
    this.ws = null;
    this.isConnected = false;
    console.log(`[RemoteProxy] CONSTRUCTED. Initial isConnected: ${this.isConnected}`);
  }

  /**
   * 注入 HookManager 依赖。
   * @param {import('./HookManager.js').HookManager} hookManager 
   */
  setHookManager(hookManager) {
    this.localHookManager = hookManager;
  }

  connect() {
    if (this.ws) {
        // 防止重复连接
        return;
    }
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/hooks`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("🔗 WebSocket connection established.");
      this.isConnected = true;
      if (this.localHookManager) {
        // 在 `addImplementation` 调用时，`globalHookRegistry` 已经知道这个钩子了
        this.localHookManager.addImplementation('websocket.connected', () => {});
        this.localHookManager.trigger('websocket.connected');
      }

      // 【已移除】不再在此处同步钩子。
      // this.syncFrontendHooks(); 
    };
    
    this.ws.onmessage = (event) => this.handleIncoming(event);
    
    this.ws.onclose = () => {
      console.warn("🔌 WebSocket connection closed. Attempting to reconnect in 3 seconds...");
      if (this.isConnected) {
        this.isConnected = false;
        if (this.localHookManager) {
            // 确保钩子存在
            this.localHookManager.addImplementation('websocket.disconnected', () => {});
            this.localHookManager.trigger('websocket.disconnected');
        }
      }
      this.ws = null; // 清理实例以允许重新连接
      setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }
  
  /**
   * 将前端实现的钩子清单发送到后端。
   */
  syncFrontendHooks() {
    if (!this.localHookManager) {
        console.error("[RemoteProxy] 无法同步钩子，HookManager 未设置。");
        return;
    }
    // 添加一个延迟/重试机制，以防 `sync` 被调用时 WS 尚未完全打开
    const trySync = (retries = 5) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          const hookNamesArray = this.localHookManager.getAllHookNames();
          const payload = {
              type: 'sync_hooks', // 特殊类型
              hooks: hookNamesArray
          };
          const message = JSON.stringify(payload);
          console.log(`[ws >] 正在与后端同步 ${hookNamesArray.length} 个前端钩子。`);
          this.ws.send(message);
      } else if (retries > 0) {
          console.warn(`[RemoteProxy] WebSocket 未打开，将在 200ms 后重试同步 (剩余次数: ${retries - 1})`);
          setTimeout(() => trySync(retries - 1), 200);
      } else {
          console.error("[RemoteProxy] 无法同步钩子: WebSocket 未打开且已达到重试次数上限。");
      }
    }
    trySync();
  }

  handleIncoming(event) {
    try {
      const payload = JSON.parse(event.data);
      if (payload.hook_name) {
        console.log(`[ws <] 收到远程钩子: ${payload.hook_name}`, payload.data);
        if (this.localHookManager) {
          // 关键：直接执行本地实现，绕过智能路由，以防止无限循环。
          // 后端的 HookManager.trigger 已经确定这个钩子应该在前端本地运行。
          const implementations = this.localHookManager.hooks.get(payload.hook_name) || [];
          const tasks = implementations.map(impl => Promise.resolve(impl(payload.data || {})));
          Promise.all(tasks);
        }
      }
    } catch (e) {
      console.error("解析传入的 WebSocket 消息失败:", e);
    }
  }

  /**
   * 将一个钩子触发消息发送到后端。
   * 这个方法由本地 HookManager 的智能路由逻辑调用。
   * @param {string} hookName 
   * @param {object} data 
   */
  trigger(hookName, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = { hook_name: hookName, data };
      console.log(`[ws >] 正在触发远程钩子: ${hookName}`, data);
      this.ws.send(JSON.stringify(payload));
    } else {
      console.error("无法触发远程钩子: WebSocket 未打开。");
    }
  }
}