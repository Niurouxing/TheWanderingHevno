// plugins/core_llm_config/src/utils/api.js

const BASE_URL = '/api/llm/config';

export async function fetchKeyConfig(providerName) {
    const response = await fetch(`${BASE_URL}/${providerName}`);
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "API query failed." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}

export async function updateKeyConfig(providerName, keys) {
    const response = await fetch(`${BASE_URL}/${providerName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "API update failed." }));
        throw new Error(err.detail || `HTTP Error ${response.status}`);
    }
    return response.json();
}