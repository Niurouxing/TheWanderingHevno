// plugins/core_runner_ui/src/api.js

const BASE_URL = '/api/sandboxes';

export async function getSandboxDetails(sandboxId) {
    const response = await fetch(`${BASE_URL}/${sandboxId}`); // 使用标准的 GET /resource/{id}
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: `Failed to fetch details for sandbox ${sandboxId}.` }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}

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

    // 保持原有的错误处理
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Step API call failed." }));
        return {
            status: "ERROR",
            error_message: err.detail || `HTTP Error ${response.status}`,
            sandbox: null,
        }
    }
    return response.json();
}

/**
 * 获取沙盒的完整快照历史
 */
export async function getHistory(sandboxId) {
    const response = await fetch(`${BASE_URL}/${sandboxId}/history`);
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Failed to get history." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}

/**
 * 将沙盒回滚到指定的快照
 */
export async function revert(sandboxId, snapshotId) {
    const response = await fetch(`${BASE_URL}/${sandboxId}/revert`, {
        method: 'PUT', // 注意: 你的后端可能是 POST 或 PUT，根据实际情况调整
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ snapshot_id: snapshotId }),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Revert operation failed." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}