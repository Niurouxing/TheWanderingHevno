/**
 * 负责管理与后端 WebSocket 的连接，并作为前后端钩子系统的桥梁。
 */
export class RemoteHookProxy {
  /**
   * @param {import('./HookManager').HookManager} localHookManager - 前端本地的钩子管理器实例。
   */
  constructor(localHookManager) {
    this.localHookManager = localHookManager;
    this.ws = null;
  }

  /**
   * 建立并维护 WebSocket 连接。
   */
  connect() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/hooks`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => console.log("🔗 WebSocket connection established.");
    
    this.ws.onmessage = (event) => this.handleIncoming(event);
    
    this.ws.onclose = () => {
      console.warn("🔌 WebSocket connection closed. Attempting to reconnect in 3 seconds...");
      setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (error) => console.error("WebSocket error:", error);
  }

  /**
   * 处理从后端接收到的消息，并将其转发到前端钩子系统。
   * @param {MessageEvent} event - WebSocket 消息事件。
   */
  handleIncoming(event) {
    try {
      const payload = JSON.parse(event.data);
      if (payload.hook_name) {
        console.log(`[ws <] Received remote hook: ${payload.hook_name}`, payload.data);
        // 将后端事件转发到前端钩子系统
        this.localHookManager.trigger(payload.hook_name, payload.data);
      }
    } catch (e) {
      console.error("Failed to parse incoming WebSocket message:", e);
    }
  }

  /**
   * 供前端插件调用，以触发一个后端的钩子。
   * @param {string} hookName - 要在后端触发的钩子名称。
   * @param {object} data - 要发送的数据。
   */
  trigger(hookName, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = { hook_name: hookName, data };
      console.log(`[ws >] Triggering remote hook: ${hookName}`, data);
      this.ws.send(JSON.stringify(payload));
    } else {
      console.error("Cannot trigger remote hook: WebSocket is not open.");
    }
  }
}