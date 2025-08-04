// frontend/packages/kernel/src/APIService.ts
type Interceptor = (request: Request) => Request | Promise<Request>;

export class APIService {
  private requestInterceptors: Interceptor[] = [];
  private baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  public addRequestInterceptor(interceptor: Interceptor) {
    this.requestInterceptors.push(interceptor);
  }

  private async applyInterceptors(request: Request): Promise<Request> {
    let req = request;
    for (const interceptor of this.requestInterceptors) {
      req = await interceptor(req);
    }
    return req;
  }

  public async get<T>(endpoint: string): Promise<T> {
    let request = new Request(`${this.baseUrl}${endpoint}`, { method: 'GET' });
    request = await this.applyInterceptors(request);
    const response = await fetch(request);
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
  }
  
  // 实现 post, put, delete...
}