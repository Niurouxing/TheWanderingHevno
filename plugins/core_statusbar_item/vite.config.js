import { defineConfig } from 'vite';
import { resolve } from 'path';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => { // <-- 接收 mode 参数
  return {
    plugins: [react()],
    // 【新增】定义一个全局常量替换
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    build: {
      lib: {
        entry: resolve(__dirname, 'src/main.jsx'),
        name: 'HevnoCoreStatusbarItem',
        fileName: 'main',
        formats: ['es'],
      },
      outDir: 'dist',
      emptyOutDir: true,
    },
  };
});