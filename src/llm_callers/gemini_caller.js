// src/llm_callers/gemini_caller.js

import { apiKeyManager } from '../core/apiKeyManager.js';
import { llmLogger } from '../utils/llm_logger.js';

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

    const { model, temperature = 1.15, topP = 0.98, maxOutputTokens = 65534} = llmConfig;
    let lastError = null;
    let retryAttempt = 0;
    const sessionId = llmLogger.generateSessionId();
    
    const startTime = Date.now();
    console.log(`[LLM-Exec] � Session ${sessionId} | Starting execution...`);
    
    // 循环，直到成功，或ApiKeyManager告知我们已无健康密钥可用
    while (true) {
        retryAttempt++;
        const key = await apiKeyManager.getHealthyKey();

        if (!key) {
            const duration = Date.now() - startTime;
            console.error(`[LLM-Exec] ❌ Session ${sessionId} | No healthy keys available | ${duration}ms`);
            throw lastError || new Error("No healthy API keys available to fulfill the request.");
        }

        try {
            console.log(`[LLM-Exec] 🔑 Session ${sessionId} | Using key ...${key.slice(-4)} | Attempt ${retryAttempt}`);
            
            const genAI = new window.GoogleGenerativeAI(key);
            const generativeModel = genAI.getGenerativeModel({
                model: model,
                generationConfig: { temperature, topP, maxOutputTokens },
            });
            const contents = [{ role: "user", parts: [{ text: prompt }] }];

            const result = await generativeModel.generateContent({ contents });
            const response = await result.response;
            const text = response.text();
            const duration = Date.now() - startTime;
            
            // 解析API响应详情
            const responseData = {
                text: text,
                candidates: response.candidates || [],
                promptFeedback: response.promptFeedback || null,
                usageMetadata: response.usageMetadata || null,
                finishReason: response.candidates?.[0]?.finishReason || 'unknown',
                safetyRatings: response.candidates?.[0]?.safetyRatings || []
            };
            
            // 技术执行层的状态日志
            if (!text || text.trim().length === 0) {
                console.warn(`[LLM-Exec] ⚠️  Session ${sessionId} | EMPTY RESPONSE | ${duration}ms`);
                console.warn(`[LLM-Exec] 🔍 Session ${sessionId} | Candidates: ${responseData.candidates.length} | Finish: ${responseData.finishReason}`);
                
                // 详细的空响应分析
                if (responseData.promptFeedback) {
                    console.warn(`[LLM-Exec] 🛡️  Session ${sessionId} | Prompt blocked:`, responseData.promptFeedback);
                }
                if (responseData.safetyRatings.length > 0) {
                    console.warn(`[LLM-Exec] 🛡️  Session ${sessionId} | Safety ratings:`, responseData.safetyRatings);
                }
                
                // 使用日志工具进行深度分析
                llmLogger.logEmptyResponse(sessionId, prompt, llmConfig, responseData, {
                    apiKey: key,
                    retryAttempt,
                    duration
                });
            } else {
                console.log(`[LLM-Exec] ✅ Session ${sessionId} | Success | ${text.length} chars | ${duration}ms`);
                
                // 记录Token使用情况
                if (responseData.usageMetadata) {
                    const usage = responseData.usageMetadata;
                    console.log(`[LLM-Exec] 📊 Session ${sessionId} | Tokens: ${usage.promptTokenCount}→${usage.candidatesTokenCount} (${usage.totalTokenCount} total)`);
                }
            }

            // 成功！释放key并返回结果
            apiKeyManager.releaseKey(key);
            return text;

        } catch (error) {
            lastError = error;
            const duration = Date.now() - startTime;
            
            console.error(`[LLM-Exec] ❌ Session ${sessionId} | Key ...${key.slice(-4)} failed | ${duration}ms`);
            console.error(`[LLM-Exec] 🔍 Session ${sessionId} | Error: ${error.name} - ${error.message}`);
            
            // 使用分析工具进行错误分析
            if (retryAttempt === 1) { // 只在第一次失败时详细分析
                llmLogger.analyzeError(error, { apiKey: key, sessionId });
            }
            
            await apiKeyManager.recordFailure(key, error);
        }
    }
}