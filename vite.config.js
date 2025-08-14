// vite.config.js (项目根目录)

import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // 加载 .env 文件中的环境变量
  const env = loadEnv(mode, process.cwd(), '');
  
  // 决定后端的 URL
  // 在 Docker 中, VITE_API_URL 会是 http://backend:8000
  // 在本地开发时, 这个变量不存在, 会回退到 http://localhost:8000
  const backendUrl = env.VITE_API_URL || 'http://localhost:8000';
  const wsBackendUrl = backendUrl.replace(/^http/, 'ws');

  return {
    plugins: [
      react({
        jsxRuntime: 'automatic',
      }),
    ],
    server: {
      // 关键变更: 动态代理
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
        '/ws': {
          target: wsBackendUrl,
          ws: true,
        },
      },
    },
  };
});