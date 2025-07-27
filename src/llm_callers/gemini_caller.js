// src/llm_callers/gemini_caller.js

import { apiKeyManager } from '../core/apiKeyManager.js';

/**
 * 【V4 - 解耦版】执行对Google Gemini API的调用。
 * 自身不包含重试逻辑，完全依赖ApiKeyManager进行密钥轮换。
 * @param {string} prompt - 完整的、渲染后的prompt。
 * @param {object} llmConfig - 来自模块定义的LLM配置。
 * @returns {Promise<string>} LLM生成的文本。
 */
export async function execute(prompt, llmConfig) {
    if (typeof window.GoogleGenerativeAI === 'undefined') {
        throw new Error("Google Generative AI SDK is not loaded.");
    }

    const { model, temperature = 0.7, topP = 1.0, maxOutputTokens = 2048 } = llmConfig;
    let lastError = null;
    
    // 循环，直到成功，或ApiKeyManager告知我们已无健康密钥可用
    while (true) {
        const key = await apiKeyManager.getHealthyKey();

        // 如果返回null，说明所有key都已被尝试、禁用或正在忙，并且没有可等待的
        if (!key) {
            throw lastError || new Error("No healthy API keys available to fulfill the request.");
        }

        try {
            console.log(`[GeminiCaller] Attempting request with key ...${key.slice(-4)}`);
            
            const genAI = new window.GoogleGenerativeAI(key);
            const generativeModel = genAI.getGenerativeModel({
                model: model,
                generationConfig: { temperature, topP, maxOutputTokens },
            });
            const contents = [{ role: "user", parts: [{ text: prompt }] }];

            const result = await generativeModel.generateContent({ contents });
            const response = await result.response;
            const text = response.text();

            // 成功！释放key并返回结果
            apiKeyManager.releaseKey(key);
            return text;

        } catch (error) {
            lastError = error;
            // 报告失败，让ApiKeyManager来决策
            await apiKeyManager.recordFailure(key, error);
            // 循环将继续，尝试获取下一个健康的key
        }
    }
}