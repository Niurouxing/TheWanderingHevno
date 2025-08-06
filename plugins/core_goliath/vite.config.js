import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
  return {
    plugins: [
      // 显式声明使用 automatic 运行时
      react({
        jsxRuntime: 'automatic' 
      }),
    ],

    define: {
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
      sourcemap: mode === 'production',
      minify: mode === 'production',
    },
  };
});