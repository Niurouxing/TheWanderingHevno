// plugins/core_layout/src/main.js

import { Layout } from './Layout.js';
import './styles.css';

/**
 * 核心布局插件的注册入口。
 * @param {object} context - 由内核注入的 ServiceContainer 实例。
 */
export function registerPlugin(context) {
    console.log('Core Layout Plugin Registered!');
    
    // 【关键修复】从 ServiceContainer 中获取 hookManager 服务
    const hookManager = context.get('hookManager');
    if (!hookManager) {
        console.error('[Core Layout] Could not get hookManager service!');
        return;
    }

    // 使用获取到的 hookManager 注册监听器
    hookManager.addImplementation('layout.mount', async (data) => {
        // 在实例化 Layout 时，将整个 context (ServiceContainer) 传入
        // Layout 组件内部会通过 context.get(...) 来获取它需要的任何服务
        const layout = new Layout(data.target, context);
        await layout.mount();
    });
}