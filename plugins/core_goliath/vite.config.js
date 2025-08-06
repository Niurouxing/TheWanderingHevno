// plugins/core_goliath/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig(({ mode }) => { // 将配置导出为一个函数，以访问 mode
  return {
    plugins: [react()],

    // 关键修复: 在这里定义全局常量替换
    // 这会在构建时将代码中所有的 `process.env.NODE_ENV` 替换为指定的字符串
    define: {
      // JSON.stringify 会将 'production' 或 'development' 变成带引号的字符串 "'production'"
      'process.env.NODE_ENV': JSON.stringify(mode === 'production' ? 'production' : 'development'),
    },

    build: {
      lib: {
        entry: resolve(__dirname, 'src/main.jsx'),
        name: 'HevnoGoliathPlugin',
        fileName: 'main',
        formats: ['es'],
      },
      outDir: 'dist',
      emptyOutDir: true,
      
      // 推荐: 在生产构建中启用 sourcemap，便于调试
      sourcemap: mode === 'production',
      
      // 推荐: 在生产构建中禁用压缩，如果需要最终调试打包后的代码
      // 如果要发布，请设置为 true
      minify: mode === 'production',
    },
  };
});