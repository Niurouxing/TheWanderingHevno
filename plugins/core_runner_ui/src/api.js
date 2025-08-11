const BASE_URL = '/api/sandboxes';

/**
 * 统一写入 API
 */
export async function mutate(sandboxId, mutations) {
  const response = await fetch(`${BASE_URL}/${sandboxId}/resource:mutate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mutations }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "API mutation failed." }));
    throw new Error(err.detail || `HTTP Error ${response.status}`);
  }
  return response.json();
}

/**
 * 统一读取 API
 */
export async function query(sandboxId, paths) {
  const response = await fetch(`${BASE_URL}/${sandboxId}/resource:query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "API query failed." }));
    throw new Error(err.detail || `HTTP Error ${response.status}`);
  }
  const data = await response.json();
  return data.results;
}


/**
 * 执行沙盒计算步骤 API
 */
export async function step(sandboxId, input) {
    const response = await fetch(`${BASE_URL}/${sandboxId}/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Step API call failed." }));
        // 将错误包装成与成功响应相似的结构，以便于处理
        return {
            status: "ERROR",
            error_message: err.detail || `HTTP Error ${response.status}`,
            sandbox: null,
        }
    }
    return response.json();
}