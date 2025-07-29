// packages/core-engine/src/runners/LlmRunner.ts
import { ProcessorNode, LlmRuntime } from '@hevno/schemas';
import OpenAI from 'openai';
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai'; // 导入 Gemini SDK
import { INodeRunner, ExecutionContext, CoreServices } from '../types';
import { resolveTemplate } from '../TemplateResolver';

// 定义一个通用的 LLM 客户端接口，以便未来扩展
interface ILlmClient {
  generate(runtime: LlmRuntime, prompt: string): Promise<string | null>;
}

// =================================================================
// 具体的 LLM 客户端实现
// =================================================================

class OpenAiClient implements ILlmClient {
  private client: OpenAI;
  constructor(apiKey: string) {
    this.client = new OpenAI({ apiKey });
  }

  async generate(runtime: LlmRuntime, prompt: string): Promise<string | null> {
    const completion = await this.client.chat.completions.create({
      model: runtime.model,
      temperature: runtime.temperature,
      messages: [
        ...(runtime.systemPrompt ? [{ role: 'system' as const, content: runtime.systemPrompt }] : []),
        { role: 'user', content: prompt },
      ],
    });
    return completion.choices[0].message.content;
  }
}

class GeminiClient implements ILlmClient {
  private client: GoogleGenerativeAI;
  constructor(apiKey: string) {
    this.client = new GoogleGenerativeAI(apiKey);
  }

  async generate(runtime: LlmRuntime, prompt: string): Promise<string | null> {
    const model = this.client.getGenerativeModel({ 
        model: runtime.model,
        // Gemini 的 System Prompt 在这里设置
        systemInstruction: runtime.systemPrompt,
    });
    
    const result = await model.generateContent({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: {
            temperature: runtime.temperature,
        },
        // 安全设置，根据需要调整。这里设置为较低的屏蔽阈值。
        safetySettings: [
            { category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE },
            { category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE },
            { category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE },
            { category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE },
        ],
    });

    return result.response.text();
  }
}


// =================================================================
// LlmRunner 现在是一个调度器
// =================================================================

export class LlmRunner implements INodeRunner {
  private clients: Map<string, ILlmClient> = new Map();

  private getClient(provider: 'openai' | 'gemini'): ILlmClient {
    if (this.clients.has(provider)) {
      return this.clients.get(provider)!;
    }

    let client: ILlmClient;
    if (provider === 'openai') {
      const apiKey = process.env.OPENAI_API_KEY;
      if (!apiKey) throw new Error("OPENAI_API_KEY is not set in environment variables for 'openai' provider.");
      client = new OpenAiClient(apiKey);
    } else if (provider === 'gemini') {
      const apiKey = process.env.GEMINI_API_KEY; // <-- 重要: 使用 GEMINI_API_KEY
      if (!apiKey) throw new Error("GEMINI_API_KEY is not set in environment variables for 'gemini' provider.");
      client = new GeminiClient(apiKey);
    } else {
      throw new Error(`Unsupported LLM provider: ${provider}`);
    }

    this.clients.set(provider, client);
    return client;
  }

  async run(
    node: ProcessorNode,
    inputs: Record<string, any>,
    context: ExecutionContext,
    services: CoreServices
  ): Promise<Record<string, any>> {
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
    let outputData: Record<string, any> = {};
    try {
      if (content) {
        outputData = JSON.parse(content);
        // 如果解析出来不是一个对象 (比如是数组或字符串), 则包装一下
        if (typeof outputData !== 'object' || outputData === null || Array.isArray(outputData)) {
            outputData = { output: outputData };
        }
      }
    } catch (e) {
      // 默认将纯文本放在 'output' 端口
      outputData = { output: content };
    }

    return outputData;
  }
}