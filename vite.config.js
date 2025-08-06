import { defineConfig } from 'vite';
// import { resolve } from 'path'; // 不再需要

export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      // 在生产构建后，需要一个服务器（如 Nginx 或后端）来处理 /plugins 请求
      // 但在开发时，我们让 Vite 直接服务于 /plugins/... 的源文件，所以这里不能有代理
    },
  },
  // resolve.alias 配置项已被移除
});