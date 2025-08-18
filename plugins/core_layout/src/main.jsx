// plugins/core_layout/src/main.jsx
import React from 'react';
import { LayoutProvider } from './context/LayoutContext';
import { createRoot } from 'react-dom/client';
import { App } from './App';
// --- 1. 导入 ConfirmationService ---
import { ConfirmationService } from './services/ConfirmationService';

// 全局标志位，防止开发模式下的热重载重复执行
if (typeof window.hevnoCoreLayoutInitialized === 'undefined') {
  window.hevnoCoreLayoutInitialized = false;
}

/**
 * Hevno 插件系统的入口函数。
 * 由前端加载器在加载此插件时调用。
 * @param {import('../../../../frontend/ServiceContainer').ServiceContainer} context - 平台服务容器
 */
export function registerPlugin(context) {
  if (window.hevnoCoreLayoutInitialized) {
    console.warn('[core_layout] Attempted to re-register. Aborting.');
    return;
  }
  
  const hookManager = context.get('hookManager');
  if (!hookManager) {
    console.error('[core_layout] CRITICAL: HookManager service not found!');
    return;
  }

  // --- 2. 创建服务实例并注册到全局服务容器 ---
  const confirmationService = new ConfirmationService();
  context.register('confirmationService', confirmationService, 'core_layout');

  // 监听内核加载器发出的“就绪”信号
  // 这是我们接管UI的最佳时机
  hookManager.addImplementation('loader.ready', () => {
    // 双重检查
    if (window.hevnoCoreLayoutInitialized) return;
    window.hevnoCoreLayoutInitialized = true;

    console.log('[core_layout] Received "loader.ready". Initializing React application host...');

    // 1. 找到根DOM容器
    const appContainer = document.getElementById('app');
    if (!appContainer) {
      console.error('[core_layout] CRITICAL: #app container not found in DOM!');
      return;
    }

    // 2. 清空容器，为React应用做准备
    appContainer.innerHTML = '';

    // 3. 创建并渲染React应用
    const root = createRoot(appContainer);
    root.render(
    <React.StrictMode>
        {/* 将平台服务注入到 React 世界 */}
        <LayoutProvider services={context}> 
        <App />
        </LayoutProvider>
    </React.StrictMode>
    );

    console.log('[core_layout] React host mounted successfully.');

    // 4. (未来) 在这里可以触发一个新的钩子，比如 'host.ready'
    // hookManager.trigger('host.ready');
  });
}