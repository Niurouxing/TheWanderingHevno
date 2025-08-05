// plugins/core_layout/src/main.js
import { Layout } from './Layout.js';
//【移除】不再直接导入 CSS
// import './styles.css';

/**
 * 动态加载 CSS 文件并将其注入到文档的 <head> 中。
 * @param {string} url - CSS 文件的 URL。
 */
function loadCSS(url) {
  // 检查是否已加载，避免重复
  if (document.querySelector(`link[href="${url}"]`)) {
    return;
  }
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = url;
  document.head.appendChild(link);
}

/**
 * 核心布局插件的注册入口。
 * @param {object} context - 由内核注入的核心服务上下文。
 */
export function registerPlugin(context) {
    console.log('Core Layout Plugin Registered!');
    
    // 【新增】在注册时，就加载本插件所需的 CSS
    // Vite 的代理会正确处理这个相对路径
    loadCSS('/plugins/core_layout/dist/styles.css');

    context.hookManager.addImplementation('layout.mount', async (data) => {
        const layout = new Layout(data.target);
        await layout.mount();
    });
}