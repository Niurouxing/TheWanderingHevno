// src/utils/llm_logger.js

import { DEBUG_CONFIG, shouldLog, getLogConfig } from './debug_config.js';

/**
 * LLM调用专用分析工具
 * 专注于问题诊断和深度分析，不重复基础日志
 */
export class LLMLogger {
    
    /**
     * 记录空响应的详细分析（这是最重要的功能）
     */
    static logEmptyResponse(sessionId, prompt, llmConfig, apiResponse, context = {}) {
        const timestamp = new Date().toISOString();
        
        console.group(`🔍 [LLM-Analysis] EMPTY RESPONSE - ${sessionId} - ${timestamp}`);
        console.warn('⚠️  Empty response detected, analyzing possible causes...');
        
        // 基本信息
        console.log('📋 Context:', {
            promptLength: prompt.length,
            model: llmConfig.model,
            temperature: llmConfig.temperature,
            maxTokens: llmConfig.maxOutputTokens,
            apiKey: context.apiKey ? `...${context.apiKey.slice(-4)}` : 'unknown'
        });
        
        // 分析API响应结构
        console.group('🕵️  API Response Analysis:');
        
        if (!apiResponse.candidates || apiResponse.candidates.length === 0) {
            console.warn('❌ No candidates returned by API - possible request rejection');
        } else {
            console.log(`✅ ${apiResponse.candidates.length} candidate(s) available`);
            
            const candidate = apiResponse.candidates[0];
            if (candidate.finishReason !== 'STOP') {
                console.warn(`❌ Unusual finish reason: ${candidate.finishReason}`);
                if (candidate.finishReason === 'SAFETY') {
                    console.warn('🛡️  Content filtered by safety system');
                } else if (candidate.finishReason === 'MAX_TOKENS') {
                    console.warn('📏 Response truncated due to token limit');
                }
            }
        }
        
        if (apiResponse.promptFeedback) {
            console.warn('🛡️  Prompt feedback (content policy):');
            console.warn(apiResponse.promptFeedback);
        }
        
        if (apiResponse.safetyRatings && apiResponse.safetyRatings.length > 0) {
            const blockedRatings = apiResponse.safetyRatings.filter(rating => 
                rating.probability === 'HIGH' || rating.probability === 'MEDIUM'
            );
            if (blockedRatings.length > 0) {
                console.warn('🚨 Safety concerns detected:');
                blockedRatings.forEach(rating => {
                    console.warn(`  - ${rating.category}: ${rating.probability}`);
                });
            }
        }
        
        console.groupEnd();
        
        // 分析可能的原因
        console.group('💡 Possible Solutions:');
        
        if (prompt.length > 30000) {
            console.log('📏 Try reducing prompt length (current: >30k chars)');
        }
        
        if (llmConfig.maxOutputTokens && llmConfig.maxOutputTokens < 100) {
            console.log('🔧 Try increasing maxOutputTokens (current: <100)');
        }
        
        if (llmConfig.temperature === 0) {
            console.log('🎲 Try increasing temperature for more creativity');
        }
        
        if (apiResponse.promptFeedback || (apiResponse.safetyRatings && apiResponse.safetyRatings.length > 0)) {
            console.log('📝 Try rephrasing prompt to avoid content policy triggers');
        }
        
        if (context.retryAttempt > 1) {
            console.log('🔄 Consider checking API key quota and status');
        }
        
        console.groupEnd();
        console.groupEnd();
    }
    
    /**
     * 生成会话ID用于跟踪单次LLM调用
     */
    static generateSessionId() {
        return Math.random().toString(36).substring(2, 8).toUpperCase();
    }
    
    /**
     * 分析API错误
     */
    static analyzeError(error, context = {}) {
        console.group('🔍 [LLM-Analysis] ERROR ANALYSIS');
        
        if (error.status === 429) {
            console.error('🚫 Rate limit exceeded - API quota exhausted');
            console.log('💡 Solutions: Wait for quota reset, use different API key, or reduce request frequency');
        } else if (error.status === 401 || error.status === 403) {
            console.error('🔑 Authentication/Authorization failed');
            console.log('💡 Solutions: Check API key validity, permissions, and billing status');
        } else if (error.status >= 500) {
            console.error('🔥 Server error - API service issue');
            console.log('💡 Solutions: Retry after delay, check API status page');
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('🌐 Network connectivity issue');
            console.log('💡 Solutions: Check internet connection, proxy settings, firewall');
        } else {
            console.error(`❓ Unknown error: ${error.name} - ${error.message}`);
        }
        
        if (context.apiKey) {
            console.log(`🔑 API Key: ...${context.apiKey.slice(-4)}`);
        }
        
        console.groupEnd();
    }
}

// 全局可用的便捷函数
export const llmLogger = LLMLogger;
