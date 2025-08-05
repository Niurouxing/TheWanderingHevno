import { defineConfig } from 'vite';
import { resolve } from 'path';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  return {
    plugins: [react()],
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    build: {
      lib: {
        entry: resolve(__dirname, 'src/main.jsx'),
        name: 'HevnoCoreRunner', // 插件的唯一名称
        fileName: 'main',
        formats: ['es'],
      },
      outDir: 'dist',
      emptyOutDir: true,
      // 关键：将共享依赖外部化
      rollupOptions: {
        external: ['react', 'react-dom', 'react-dom/client'],
      },
    },
  };
});