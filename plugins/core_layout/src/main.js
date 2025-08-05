// plugins/core_layout/src/main.js

import { Layout } from './Layout.js';
import './styles.css';

/**
 * 核心布局插件的注册入口。
 * @param {object} context - 由内核注入的核心服务上下文。
 */
export function registerPlugin(context) {
    console.log('Core Layout Plugin Registered!');
    
    // 监听 'layout.mount' 钩子
    context.hookManager.addImplementation('layout.mount', async (data) => {
        // 在实例化 Layout 时，将 context 和 targetElement 都传入
        const layout = new Layout(data.target, context);
        await layout.mount();
    });
}