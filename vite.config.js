// vite.config.js (项目根目录)

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react'; // <-- 在这里导入 react 插件

export default defineConfig({
  // 关键: 将 react 插件应用在根级别
  plugins: [
    react({
      // 确保整个项目都使用新的 JSX 转换
      jsxRuntime: 'automatic',
    }),
  ],

  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
});