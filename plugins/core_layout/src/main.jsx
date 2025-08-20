// plugins/core_layout/src/main.jsx
import React from 'react';
import { LayoutProvider, LayoutContext, useLayout } from './context/LayoutContext';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { ConfirmationService } from './services/ConfirmationService';

if (typeof window.hevnoCoreLayoutInitialized === 'undefined') {
  window.hevnoCoreLayoutInitialized = false;
}

/**
 * 新的应用宿主初始化函数。
 * 由前端加载器在找到 'frontend.host' 贡献点后调用。
 * @param {import('../../../../frontend/ServiceContainer').ServiceContainer} context - 平台服务容器
 */
export function initializeUI(context) {
  if (window.hevnoCoreLayoutInitialized) return;
  window.hevnoCoreLayoutInitialized = true;

  console.log('[core_layout] Received "initializeUI" call. Initializing React application host...');

  const appContainer = document.getElementById('app');
  if (!appContainer) {
    console.error('[core_layout] CRITICAL: #app container not found in DOM!');
    return;
  }

  appContainer.innerHTML = '';

  const root = createRoot(appContainer);
  root.render(
    <React.StrictMode>
      <LayoutProvider services={context}> 
        <App />
      </LayoutProvider>
    </React.StrictMode>
  );

  console.log('[core_layout] React host mounted successfully.');
}

/**
 * Hevno 插件系统的服务注册入口。
 * 由前端加载器在加载此插件时调用，仅用于注册服务。
 * @param {import('../../../../frontend/ServiceContainer').ServiceContainer} context - 平台服务容器
 */
export function registerPlugin(context) {
  if (window.hevnoCoreLayoutInitialized) {
    console.warn('[core_layout] Attempted to re-register services. Aborting.');
    return;
  }
  
  const hookManager = context.get('hookManager');
  if (!hookManager) {
    console.error('[core_layout] CRITICAL: HookManager service not found!');
    return;
  }

  // 注册此插件提供的服务
  const confirmationService = new ConfirmationService();
  context.register('confirmationService', confirmationService, 'core_layout');

  // [新增] 注册LayoutContext和useLayout钩子
  context.register('layoutContext', LayoutContext, 'core_layout');
  context.register('useLayout', useLayout, 'core_layout');

  console.log('[core_layout] Registered shared services: layoutContext, useLayout');

    // 注意：不再监听 'loader.ready' 钩子
}