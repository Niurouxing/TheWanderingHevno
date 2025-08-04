// frontend/packages/kernel/src/ServiceRegistry.ts

export class ServiceRegistry {
  private services = new Map<string, any>();

  public register<T>(name: string, instance: T): void {
    if (this.services.has(name)) {
      console.warn(`Service "${name}" is being overwritten.`);
    }
    this.services.set(name, instance);
  }

  public resolve<T>(name: string): T {
    const service = this.services.get(name);
    if (!service) {
      throw new Error(`Service "${name}" not found.`);
    }
    return service as T;
  }
}