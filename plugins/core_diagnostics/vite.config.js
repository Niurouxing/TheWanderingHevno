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
        name: 'HevnoCoreDiagnostics', // <-- 更新名称
        fileName: 'main',
        formats: ['es'],
      },
      outDir: 'dist',
      emptyOutDir: true,
    },
  };
});