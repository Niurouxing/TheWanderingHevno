import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    // 代理所有对后端的请求
    proxy: {
      // API 请求, e.g., /api/plugins/manifest
      '/api': 'http://localhost:8000',

      // WebSocket 连接
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },

      // 【关键】代理插件静态资源请求
      // 这使得内核可以通过 /plugins/... URL 加载由后端服务的插件资源
      '/plugins': 'http://localhost:8000',
    },
  },
});