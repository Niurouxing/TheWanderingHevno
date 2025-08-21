// plugins/core_llm_config/src/utils/api.js

const BASE_URL = '/api/llm/config';

// [新增] 获取所有已注册的提供商
export async function fetchProviders() {
    const response = await fetch(`${BASE_URL}/providers`);
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "无法获取提供商列表" }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    const data = await response.json();
    return data.providers || [];
}

// [新增] 触发后端热重载配置
export async function reloadConfig() {
    const response = await fetch(`${BASE_URL}/reload`, {
        method: 'POST'
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "重载请求失败" }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}

export async function fetchKeyConfig(providerName) {
    const response = await fetch(`${BASE_URL}/${providerName}`);
    if (!response.ok) {
        // 提供一个友好的默认值，以防提供商没有配置任何密钥
        if (response.status === 404) {
            return { provider: providerName, keys: [] };
        }
        const err = await response.json().catch(() => ({ detail: "API query failed." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}

export async function addKey(providerName, key) {
    const response = await fetch(`${BASE_URL}/${providerName}/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Failed to add key." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}

export async function deleteKey(providerName, keySuffix) {
    // 从 "..." 中提取最后4位
    const suffix = keySuffix.slice(-4);
    const response = await fetch(`${BASE_URL}/${providerName}/keys/${suffix}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Failed to delete key." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    // DELETE请求成功时通常没有响应体，直接返回成功状态
    return { message: "Delete successful" };
}