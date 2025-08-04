// frontend/packages/kernel/src/ServiceBus.ts
type EventHandler = (payload?: any) => void;

export class ServiceBus {
  private events = new Map<string, Set<EventHandler>>();

  public on(eventName: string, handler: EventHandler): () => void {
    if (!this.events.has(eventName)) {
      this.events.set(eventName, new Set());
    }
    this.events.get(eventName)!.add(handler);
    
    // 返回一个取消订阅的函数，非常实用
    return () => this.off(eventName, handler);
  }

  public off(eventName: string, handler: EventHandler): void {
    const handlers = this.events.get(eventName);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  public emit(eventName: string, payload?: any): void {
    const handlers = this.events.get(eventName);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(payload);
        } catch (e) {
          console.error(`Error in event handler for "${eventName}":`, e);
        }
      });
    }
  }
}