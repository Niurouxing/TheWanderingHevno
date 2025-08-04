// frontend/apps/workbench/vite.config.ts

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      jsxImportSource: '@emotion/react', // 告诉 Vite 使用 Emotion 的 JSX 运行时
      babel: {
        plugins: ['@emotion/babel-plugin'], // 添加 Emotion 的 Babel 插件
      },
    }),
  ],
  server: {
    // 配置开发服务器代理，解决跨域问题
    proxy: {
      // 代理所有 /api 开头的请求
      '/api': {
        target: 'http://localhost:8000', // 你的后端服务器地址
        changeOrigin: true, // 需要虚拟主机站点
      },
      // 代理所有 /plugins 开头的请求，用于加载插件静态资源
      '/plugins': {
        target: 'http://localhost:8000', // 你的后端服务器地址
        changeOrigin: true,
      },
      // 代理 WebSocket 连接
      '/ws': {
        target: 'ws://localhost:8000',    // 你的后端 WebSocket 地址
        ws: true,                         // 开启 WebSocket 代理
        changeOrigin: true,
      },
    },
  },
});