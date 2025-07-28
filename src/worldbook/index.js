// src/worldbook/index.js

/**
 * 世界书模块主入口
 * 
 * 这个模块提供了一个完整的世界书处理系统，包括：
 * - 从JSON文件加载世界书数据
 * - 关键词匹配和条件激活
 * - 递归处理支持
 * - 多种插入位置支持
 * - 概率激活
 * - 调试和测试工具
 */

export { WorldInfoLoader, worldInfoLoader } from './loader.js';
export { WorldInfoProcessor, WORLD_INFO_LOGIC, WORLD_INFO_POSITION } from './processor.js';
export { WorldInfoManager, worldInfoManager } from './manager.js';

// 便捷导出：最常用的API
export { worldInfoManager as default } from './manager.js';
