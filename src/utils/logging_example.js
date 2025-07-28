// src/utils/logging_example.js

/**
 * 日志系统使用示例和配置指南
 */

import { DEBUG_CONFIG, setLogLevel } from './debug_config.js';
import { llmLogger } from './llm_logger.js';

// =============================================================================
// 使用示例
// =============================================================================

/**
 * 示例1：生产环境配置
 * 只显示警告和错误，保持日志简洁
 */
function setupProductionLogging() {
    setLogLevel('WARN');
    DEBUG_CONFIG.LLM_LOGS.INCLUDE_FULL_PROMPT = false;
    DEBUG_CONFIG.LLM_LOGS.INCLUDE_FULL_RESPONSE = false;
    
    console.log('✅ Production logging configured - minimal output');
}

/**
 * 示例2：开发环境配置
 * 显示详细信息，便于调试
 */
function setupDevelopmentLogging() {
    setLogLevel('DEBUG');
    DEBUG_CONFIG.LLM_LOGS.INCLUDE_FULL_PROMPT = true;
    DEBUG_CONFIG.LLM_LOGS.INCLUDE_FULL_RESPONSE = true;
    
    console.log('✅ Development logging configured - verbose output');
}

/**
 * 示例3：故障排除配置
 * 专注于错误分析和空响应诊断
 */
function setupTroubleshootingLogging() {
    setLogLevel('INFO');
    DEBUG_CONFIG.LLM_LOGS.EMPTY_RESPONSE_ANALYSIS = true;
    DEBUG_CONFIG.LLM_LOGS.INCLUDE_API_DETAILS = true;
    
    console.log('✅ Troubleshooting logging configured - focused on issues');
}

/**
 * 示例4：静默模式
 * 只记录严重错误
 */
function setupSilentLogging() {
    setLogLevel('ERROR');
    Object.keys(DEBUG_CONFIG).forEach(key => {
        if (typeof DEBUG_CONFIG[key] === 'object') {
            Object.keys(DEBUG_CONFIG[key]).forEach(subKey => {
                if (subKey !== 'ENABLED') {
                    DEBUG_CONFIG[key][subKey] = false;
                }
            });
        }
    });
    
    console.log('✅ Silent logging configured - errors only');
}

// =============================================================================
// 快速配置函数
// =============================================================================

/**
 * 根据环境自动配置日志
 */
export function autoConfigureLogging() {
    const isDevelopment = process.env.NODE_ENV === 'development' || 
                         window.location.hostname === 'localhost';
    
    if (isDevelopment) {
        setupDevelopmentLogging();
    } else {
        setupProductionLogging();
    }
}

/**
 * 运行时切换日志级别
 */
export function switchLoggingMode(mode) {
    switch (mode.toLowerCase()) {
        case 'production':
        case 'prod':
            setupProductionLogging();
            break;
        case 'development':
        case 'dev':
            setupDevelopmentLogging();
            break;
        case 'troubleshoot':
        case 'debug':
            setupTroubleshootingLogging();
            break;
        case 'silent':
        case 'quiet':
            setupSilentLogging();
            break;
        default:
            console.warn(`Unknown logging mode: ${mode}`);
            console.log('Available modes: production, development, troubleshoot, silent');
    }
}

// =============================================================================
// 浏览器控制台辅助函数
// =============================================================================

/**
 * 在浏览器控制台中可用的调试函数
 */
if (typeof window !== 'undefined') {
    window.HevnoLogging = {
        // 快速切换日志模式
        setMode: switchLoggingMode,
        
        // 获取当前配置
        getConfig: () => DEBUG_CONFIG,
        
        // 分析最近的空响应（如果有的话）
        analyzeLastEmpty: () => {
            console.log('This would analyze the last empty response if tracking was enabled');
        },
        
        // 显示帮助信息
        help: () => {
            console.log(`
🔧 Hevno Logging Controls:

HevnoLogging.setMode('production')    - 生产模式（简洁日志）
HevnoLogging.setMode('development')   - 开发模式（详细日志）
HevnoLogging.setMode('troubleshoot')  - 故障排除模式
HevnoLogging.setMode('silent')        - 静默模式（仅错误）

HevnoLogging.getConfig()              - 查看当前配置
HevnoLogging.help()                   - 显示此帮助

Example:
  HevnoLogging.setMode('dev')         - 切换到开发模式
            `);
        }
    };
    
    console.log('🔧 Hevno logging controls available. Type HevnoLogging.help() for commands.');
}

// =============================================================================
// 自动初始化
// =============================================================================

// 自动配置（如果没有手动配置的话）
if (typeof window !== 'undefined' && !window.HEVNO_LOGGING_CONFIGURED) {
    autoConfigureLogging();
    window.HEVNO_LOGGING_CONFIGURED = true;
}
