// frontend/packages/kernel/src/APIService.ts
type Interceptor = (request: Request) => Request | Promise<Request>;

export class APIService {
  private requestInterceptors: Interceptor[] = [];
  private baseUrl = '';

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
  

public async post<T>(endpoint: string, body: any): Promise<T> {
    const request = new Request(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const finalRequest = await this.applyInterceptors(request);
    const response = await fetch(finalRequest);
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    // 201 Created 通常也有响应体
    if (response.status === 204) return null as T; // 204 No Content
    return response.json();
}

public async put<T>(endpoint: string, body: any): Promise<T> {
    const request = new Request(`${this.baseUrl}${endpoint}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const finalRequest = await this.applyInterceptors(request);
    const response = await fetch(finalRequest);
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
}

public async delete<T>(endpoint: string): Promise<T> {
    const request = new Request(`${this.baseUrl}${endpoint}`, { method: 'DELETE' });
    const finalRequest = await this.applyInterceptors(request);
    const response = await fetch(finalRequest);
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
}
}