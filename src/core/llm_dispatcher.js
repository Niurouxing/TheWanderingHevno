// src/core/llm_dispatcher.js

import * as geminiCaller from '../llm_callers/gemini_caller.js';
// 未来可以在这里添加更多caller:
// import * as openaiCaller from '../llm_callers/openai_caller.js';

const providers = {
    'gemini': geminiCaller,
    // 'openai': openaiCaller,
};

/**
 * 根据llmConfig中的provider，将请求分派给正确的LLM调用者。
 * @param {string} prompt - 渲染后的prompt。
 * @param {object} llmConfig - 模块的LLM配置。
 * @returns {Promise<string>} 来自LLM的响应。
 */
export async function dispatch(prompt, llmConfig) {
    const providerName = llmConfig.provider;
    if (!providerName) {
        throw new Error("Module is missing 'provider' field in its 'llm' configuration.");
    }

    const caller = providers[providerName.toLowerCase()];
    if (!caller) {
        throw new Error(`Unsupported LLM provider: "${providerName}". No caller found.`);
    }

    return await caller.execute(prompt, llmConfig);
}