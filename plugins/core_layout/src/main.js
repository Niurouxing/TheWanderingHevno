import { Layout } from './Layout.js';
import './styles.css'; // <-- Vite 在构建时会处理这个导入

/**
 * 核心布局插件的注册入口。
 * @param {object} context - 由内核注入的核心服务上下文。
 */
export function registerPlugin(context) {
    console.log('Core Layout Plugin Registered!');
    
    context.hookManager.addImplementation('layout.mount', async (data) => {
        const layout = new Layout(data.target);
        await layout.mount();
    });
}