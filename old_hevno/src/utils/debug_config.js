// src/utils/debug_config.js

/**
 * 调试和日志配置
 * 用于控制整个系统的日志输出级别
 */
export const DEBUG_CONFIG = {
    // 日志级别: 'DEBUG', 'INFO', 'WARN', 'ERROR'
    LOG_LEVEL: 'DEBUG',
    
    // LLM相关日志
    LLM_LOGS: {
        ENABLED: true,
        INCLUDE_FULL_PROMPT: true,
        INCLUDE_FULL_RESPONSE: true,
        INCLUDE_API_DETAILS: true,
        EMPTY_RESPONSE_ANALYSIS: true
    },
    
    // 节点执行日志
    NODE_EXECUTION: {
        ENABLED: true,
        INCLUDE_TIMING: true,
        INCLUDE_CONTEXT: true
    },
    
    // API密钥管理日志
    API_KEY_MANAGEMENT: {
        ENABLED: true,
        INCLUDE_KEY_ROTATION: true,
        INCLUDE_FAILURE_DETAILS: true
    },
    
    // 世界书日志
    WORLD_INFO: {
        ENABLED: true,
        INCLUDE_LOADING_DETAILS: true,
        INCLUDE_MUTEX_INFO: true
    }
};

/**
 * 设置日志级别
 */
export function setLogLevel(level) {
    DEBUG_CONFIG.LOG_LEVEL = level;
    console.log(`[Debug Config] Log level set to: ${level}`);
}

/**
 * 检查是否应该记录特定级别的日志
 */
export function shouldLog(level) {
    const levels = ['DEBUG', 'INFO', 'WARN', 'ERROR'];
    const currentLevelIndex = levels.indexOf(DEBUG_CONFIG.LOG_LEVEL);
    const requestedLevelIndex = levels.indexOf(level);
    return requestedLevelIndex >= currentLevelIndex;
}

/**
 * 获取特定功能的日志配置
 */
export function getLogConfig(feature) {
    return DEBUG_CONFIG[feature] || { ENABLED: false };
}
