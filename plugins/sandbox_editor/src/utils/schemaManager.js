// plugins/sandbox_editor/src/utils/schemaManager.js

/**
 * @fileoverview 一个用于获取和缓存后端运行时UI Schema的单例服务。
 * 它可以防止对 /api/editor/schemas 端点的重复网络请求。
 */

// 模块级变量，用于缓存Schema数据和正在进行的请求Promise
let runtimeSchemas = null;
let schemaLoadingPromise = null;
// [新增] 为 LLM 提供商数据添加缓存
let llmProviders = null;
let llmProvidersLoadingPromise = null;

/**
 * 从后端加载所有运行时的UI Schema，并将其缓存在内存中。
 * 如果已经加载或正在加载，则会返回缓存的结果或现有的Promise。
 * @returns {Promise<void>} 一个在Schema加载和缓存完成后解析的Promise。
 * @throws {Error} 如果API调用失败。
 */
export async function loadSchemas() {
  // 1. 如果已经加载，则立即返回，避免重复工作
  if (runtimeSchemas) {
    return;
  }

  // 2. 如果正在加载中，则返回现有的Promise，避免重复请求
  if (schemaLoadingPromise) {
    return schemaLoadingPromise;
  }

  // 3. 发起新的加载请求
  console.log('[SchemaManager] 开始从 /api/editor/schemas 获取UI schemas...');
  
  // 将Promise存储起来，以便后续的并发调用可以复用
  schemaLoadingPromise = (async () => {
    try {
      const response = await fetch('/api/editor/schemas');
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: '无法获取UI schemas' }));
        throw new Error(errData.detail || `HTTP Error ${response.status}`);
      }
      const data = await response.json();
      
      // 检查响应结构是否符合预期
      if (!data || !data.runtimes) {
        throw new Error("从后端收到的Schema格式无效。");
      }

      runtimeSchemas = data.runtimes;
      console.log(`[SchemaManager] 成功加载并缓存了 ${Object.keys(runtimeSchemas).length} 个运行时的Schema。`);

    } catch (error) {
      console.error('[SchemaManager] 获取UI schemas失败:', error);
      // 让调用者能够捕获到错误
      throw error; 
    } finally {
      // 请求完成后，清空Promise（无论成功或失败），以便下次可以重试
      schemaLoadingPromise = null;
    }
  })();

  return schemaLoadingPromise;
}

/**
 * [新增] 从后端加载所有LLM提供商信息，并将其缓存在内存中。
 */
export async function loadLlmProviders() {
    if (llmProviders) return;
    if (llmProvidersLoadingPromise) return llmProvidersLoadingPromise;

    console.log('[SchemaManager] 开始从 /api/llm/config/providers 获取LLM提供商列表...');
    llmProvidersLoadingPromise = (async () => {
        try {
            const response = await fetch('/api/llm/config/providers');
            if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
            const data = await response.json();
            if (!data || !Array.isArray(data.providers)) throw new Error("从后端收到的提供商列表格式无效。");
            llmProviders = data.providers;
            console.log(`[SchemaManager] 成功加载并缓存了 ${llmProviders.length} 个LLM提供商。`);
        } catch (error) {
            console.error('[SchemaManager] 获取LLM提供商列表失败:', error);
            throw error;
        } finally {
            llmProvidersLoadingPromise = null;
        }
    })();
    return llmProvidersLoadingPromise;
}

/**
 * 获取指定运行时的JSON Schema。
 * @param {string} runtimeName - 运行时的名称 (例如, "system.io.log").
 * @returns {object | null} 对应的JSON Schema对象，如果未加载或不存在则返回null。
 */
export function getSchemaForRuntime(runtimeName) {
  if (!runtimeSchemas) {
    console.warn(`[SchemaManager] 尝试在Schema加载完成前获取 '${runtimeName}' 的schema。`);
    return null;
  }
  return runtimeSchemas[runtimeName] || null;
}

/**
 * 获取所有已缓存的运行时Schema。
 * @returns {object | null} 一个以运行时名称为键，Schema为值的对象。
 */
export function getAllSchemas() {
    return runtimeSchemas;
}

/**
 * [新增] 获取所有已缓存的LLM提供商信息。
 * @returns {Array | null}
 */
export function getLlmProviders() {
    return llmProviders;
}