// src/llm_callers/gemini_caller.js

import { apiKeyManager } from '../core/apiKeyManager.js';

/**
 * 执行对Google Gemini API的调用。
 * @param {string} prompt - 完整的、渲染后的prompt。
 * @param {object} llmConfig - 来自模块定义的LLM配置。
 * @returns {Promise<string>} LLM生成的文本。
 */
export async function execute(prompt, llmConfig) {
    const { model, temperature = 0.7, topP = 1.0, maxOutputTokens = 2048 } = llmConfig;

    // 检查 window.GoogleGenerativeAI 是否已加载
    if (typeof window.GoogleGenerativeAI === 'undefined') {
        throw new Error("Google Generative AI SDK is not loaded.");
    }
    
    const key = await apiKeyManager.acquireKey();
    try {
        const genAI = new window.GoogleGenerativeAI(key);

        const generativeModel = genAI.getGenerativeModel({
            model: model,
            generationConfig: {
                temperature,
                topP,
                maxOutputTokens,
            },
        });
        
        // Gemini API 需要一个内容数组
        const contents = [{ role: "user", parts: [{ text: prompt }] }];
        
        console.log(`[GeminiCaller] Sending request to model: ${model}`);
        const result = await generativeModel.generateContent({ contents });
        const response = await result.response;
        
        return response.text();

    } catch (error) {
        console.error("[GeminiCaller] Error during API call:", error);
        // 重新抛出错误，以便Orchestrator可以捕获它
        throw new Error(`Gemini API Error: ${error.message}`);
    } finally {
        // 无论成功与否，都必须释放密钥
        apiKeyManager.releaseKey(key);
    }
}