import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    react({
      jsxRuntime: 'automatic'
    }),
  ],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/main.jsx'),
      name: 'HevnoCoreLayout',
      fileName: 'main',
      formats: ['es'],
    },
    outDir: 'dist',
    emptyOutDir: true,
  },
});