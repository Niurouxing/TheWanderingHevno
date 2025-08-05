import { defineConfig } from 'vite';
import { resolve } from 'path';
import react from '@vitejs/plugin-react';

// ++ 修改：包裹在函数中以接收 mode
export default defineConfig(({ mode }) => {
  return {
    plugins: [react()],
    // ++ 新增：定义环境变量，修复 "process is not defined" 错误
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    build: {
      lib: {
        entry: resolve(__dirname, 'src/main.jsx'),
        name: 'HevnoCoreSandboxes',
        fileName: 'main',
        formats: ['es'],
      },
      outDir: 'dist',
      emptyOutDir: true,
    },
  };
});