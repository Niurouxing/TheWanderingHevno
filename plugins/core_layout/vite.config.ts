import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [
    react({
      jsxImportSource: '@emotion/react', // 告诉 Vite 使用 Emotion 的 JSX 运行时
      babel: {
        plugins: ['@emotion/babel-plugin'], // 添加 Emotion 的 Babel 插件
      },
    }),
  ],
  build: {
    lib: {
      entry: path.resolve(__dirname, 'index.ts'),
      name: 'HevnoCoreLayout',
      fileName: 'index',
      formats: ['es'],
    },
    rollupOptions: {
      external: ['react', 'react-dom', '@hevno/frontend-sdk'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
  },
});