// plugins/panel_snapshot_history/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/SnapshotHistoryPanel.jsx'),
      name: 'HevnoPanelSnapshotHistory',
      fileName: 'main',
      formats: ['es'],
    },
    rollupOptions: {
      // 确保外部化处理那些你不想打包进库的依赖
      external: ['react', 'react-dom', '@mui/material', '@mui/icons-material'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM'
        }
      }
    },
    outDir: 'dist',
    emptyOutDir: true,
  },
});