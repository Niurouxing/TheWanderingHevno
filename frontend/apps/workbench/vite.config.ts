import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // 确保你的 monorepo 别名设置正确
      '@hevno/kernel': path.resolve(__dirname, '../../packages/kernel/src'),
      '@hevno/frontend-sdk': path.resolve(__dirname, '../../packages/frontend-sdk/src'),
    },
  },
  server: {
    proxy: {
      // 代理所有以 /plugins/ 开头的请求到后端服务器
      '/plugins': {
        target: 'http://localhost:8000', // 你的后端地址
        changeOrigin: true, // 必须为 true，否则后端可能因为 host 不匹配而拒绝
        // 这里不需要重写路径，因为前端请求的路径 /plugins/... 
        // 正是后端期望的路径。
      },
      // 同时，也代理所有 /api/ 请求
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
});