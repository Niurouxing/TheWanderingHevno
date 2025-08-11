// plugins/sandbox_editor/src/api.js

const BASE_URL = '/api/sandboxes';

/**
 * 构造一个统一的、包含多个修改指令的请求，并发送到后端的 :mutate 端点。
 * @param {string} sandboxId - 目标沙盒的ID。
 * @param {Array<object>} mutations - 一个或多个突变对象的数组。
 * @returns {Promise<object>} - 后端的响应。
 * @throws {Error} - 如果API调用失败。
 */
export async function mutate(sandboxId, mutations) {
  const response = await fetch(`${BASE_URL}/${sandboxId}/resource:mutate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mutations }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "API mutation failed with non-JSON response." }));
    throw new Error(err.detail || `HTTP Error ${response.status}`);
  }

  return response.json();
}

/**
 * 构造一个统一的、包含多个路径的请求，并发送到后端的 :query 端点。
 * @param {string} sandboxId - 目标沙盒的ID。
 * @param {Array<string>} paths - 要查询的数据路径数组。
 * @returns {Promise<object>} - 一个以路径为键，数据为值的对象。
 * @throws {Error} - 如果API调用失败。
 */
export async function query(sandboxId, paths) {
  const response = await fetch(`${BASE_URL}/${sandboxId}/resource:query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "API query failed with non-JSON response." }));
    throw new Error(err.detail || `HTTP Error ${response.status}`);
  }

  const data = await response.json();
  return data.results;
}
