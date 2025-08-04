// 1. 导入内核，这将启动所有内核服务和插件加载流程
import '@hevno/kernel/main';

// 2. 导入React相关库
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css'; // 导入你的全局样式

// 3. 在插件加载完毕后，渲染主App组件
// 我们监听 'plugins:ready' 这个由 PluginService 发出的事件
window.Hevno.services.hooks.addImplementation('plugins:ready', () => {
    ReactDOM.createRoot(document.getElementById('hevno-root')!).render(
        <React.StrictMode>
            <App />
        </React.StrictMode>
    );
});