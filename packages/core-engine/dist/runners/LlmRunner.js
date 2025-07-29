import OpenAI from 'openai';
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai'; // 导入 Gemini SDK
import { resolveTemplate } from '../TemplateResolver';
// =================================================================
// 具体的 LLM 客户端实现
// =================================================================
class OpenAiClient {
    client;
    constructor(apiKey) {
        this.client = new OpenAI({ apiKey });
    }
    async generate(runtime, prompt) {
        const completion = await this.client.chat.completions.create({
            model: runtime.model,
            temperature: runtime.temperature,
            messages: [
                ...(runtime.systemPrompt ? [{ role: 'system', content: runtime.systemPrompt }] : []),
                { role: 'user', content: prompt },
            ],
        });
        return completion.choices[0].message.content;
    }
}
class GeminiClient {
    client;
    constructor(apiKey) {
        this.client = new GoogleGenerativeAI(apiKey);
    }
    async generate(runtime, prompt) {
        const model = this.client.getGenerativeModel({
            model: runtime.model,
            systemInstruction: runtime.systemPrompt,
        });
        try { // <--- 添加 try 块
            const result = await model.generateContent({
                contents: [{ role: "user", parts: [{ text: prompt }] }],
                generationConfig: {
                    temperature: runtime.temperature,
                },
                safetySettings: [
                    { category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE },
                    { category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE },
                    { category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE },
                    { category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE },
                ],
            });
            const response = result.response;
            if (!response) {
                const blockReason = result.promptFeedback?.blockReason;
                const safetyRatings = result.promptFeedback?.safetyRatings;
                let errorMessage = `Gemini API call failed. The response was empty.`;
                if (blockReason) {
                    errorMessage += ` Reason: ${blockReason}.`;
                }
                if (safetyRatings && safetyRatings.length > 0) {
                    errorMessage += ` Safety ratings: ${JSON.stringify(safetyRatings)}`;
                }
                throw new Error(errorMessage);
            }
            return response.text();
        }
        catch (error) { // <--- 添加 catch 块
            // 捕获 API Key 无效、网络错误等所有异常
            console.error("[GeminiClient] Raw error from SDK:", error); // 打印原始错误以供调试
            // 重新抛出一个标准的 Error 对象，包含更丰富的信息
            const message = error.message || 'An unknown error occurred in GeminiClient.';
            throw new Error(`Gemini API request failed: ${message}`);
        }
    }
}
// =================================================================
// LlmRunner 现在是一个调度器
// =================================================================
export class LlmRunner {
    clients = new Map();
    getClient(provider) {
        if (this.clients.has(provider)) {
            return this.clients.get(provider);
        }
        let client;
        if (provider === 'openai') {
            const apiKey = process.env.OPENAI_API_KEY;
            if (!apiKey)
                throw new Error("OPENAI_API_KEY is not set in environment variables for 'openai' provider.");
            client = new OpenAiClient(apiKey);
        }
        else if (provider === 'gemini') {
            const apiKey = process.env.GEMINI_API_KEY; // <-- 重要: 使用 GEMINI_API_KEY
            if (!apiKey)
                throw new Error("GEMINI_API_KEY is not set in environment variables for 'gemini' provider.");
            client = new GeminiClient(apiKey);
        }
        else {
            throw new Error(`Unsupported LLM provider: ${provider}`);
        }
        this.clients.set(provider, client);
        return client;
    }
    async run(node, inputs, context, services) {
        if (node.runtime.type !== 'llm') {
            throw new Error('Invalid node type for LlmRunner');
        }
        // 1. 获取对应的客户端
        const client = this.getClient(node.runtime.provider);
        // 2. 解析模板化的 Prompt
        const finalPrompt = resolveTemplate(node.runtime.userPrompt, context);
        console.log(`[LlmRunner] Executing node ${node.name} (${node.id}) via ${node.runtime.provider} with prompt: "${finalPrompt}"`);
        // 3. 调用 LLM 服务
        const content = await client.generate(node.runtime, finalPrompt);
        // 4. 尝试将输出解析为 JSON，如果失败则作为纯文本
        let outputData = {};
        try {
            if (content) {
                outputData = JSON.parse(content);
                // 如果解析出来不是一个对象 (比如是数组或字符串), 则包装一下
                if (typeof outputData !== 'object' || outputData === null || Array.isArray(outputData)) {
                    outputData = { output: outputData };
                }
            }
        }
        catch (e) {
            // 默认将纯文本放在 'output' 端口
            outputData = { output: content };
        }
        return outputData;
    }
}
//# sourceMappingURL=LlmRunner.js.map