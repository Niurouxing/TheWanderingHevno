// ./frontend/RemoteHookProxy.js

/**
 * 负责管理与后端 WebSocket 的连接，并作为前后端钩子系统的桥梁。
 */
export class RemoteHookProxy {
  constructor(localHookManager) {
    this.localHookManager = localHookManager;
    this.ws = null;
    this.isConnected = false;
    // 【日志】
    console.log(`[RemoteProxy] CONSTRUCTED. Initial isConnected: ${this.isConnected}`);
  }

  connect() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/hooks`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("🔗 WebSocket connection established.");
      // 【日志】
      console.log(`[RemoteProxy] ON_OPEN. Setting isConnected to true.`);
      this.isConnected = true;
      this.localHookManager.trigger('websocket.connected');
    };
    
    this.ws.onmessage = (event) => this.handleIncoming(event);
    
   this.ws.onclose = () => {
      console.warn("🔌 WebSocket connection closed. Attempting to reconnect in 3 seconds...");
      if (this.isConnected) {
          // 【日志】
          console.log(`[RemoteProxy] ON_CLOSE. Was connected, now setting to false.`);
          this.isConnected = false;
          this.localHookManager.trigger('websocket.disconnected');
      }
      setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      if (this.isConnected) { // <--【修改】只有在之前是连接状态时才触发
          this.isConnected = false;
          this.localHookManager.trigger('websocket.disconnected');
      }
    };
  }
  handleIncoming(event) {
    try {
      const payload = JSON.parse(event.data);
      if (payload.hook_name) {
        console.log(`[ws <] Received remote hook: ${payload.hook_name}`, payload.data);
        this.localHookManager.trigger(payload.hook_name, payload.data);
      }
    } catch (e) {
      console.error("Failed to parse incoming WebSocket message:", e);
    }
  }

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