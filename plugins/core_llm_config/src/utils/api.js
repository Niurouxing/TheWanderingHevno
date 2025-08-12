// plugins/core_llm_config/src/utils/api.js

const BASE_URL = '/api/llm/config';

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

// [新] 添加密钥的函数
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

// [新] 删除密钥的函数
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
    return response.json();
}