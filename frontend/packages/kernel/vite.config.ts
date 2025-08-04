// packages/kernel/vite.config.ts

import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: path.resolve(__dirname, 'main.ts'),
      name: 'HevnoKernel',
      fileName: 'main',
      formats: ['es'], // 只需输出 ES Module 格式
    },
    outDir: 'dist',
    emptyOutDir: true,
  },
});