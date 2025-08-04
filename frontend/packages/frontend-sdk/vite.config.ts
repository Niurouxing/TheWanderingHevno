// packages/frontend-sdk/vite.config.ts

import { defineConfig } from 'vite';
import path from 'path';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [dts()],
  build: {
    lib: {
        // 不能使用单一入口，因为我们有多个导出路径
        entry: {
            index: path.resolve(__dirname, 'src/index.ts'),
            types: path.resolve(__dirname, 'src/types.ts')
        },
        name: 'HevnoFrontendSDK',
        formats: ['es', 'cjs']
    },
    rollupOptions: {
      // 确保外部化处理那些你不想打包进库的依赖
      external: ['react', 'react-dom'],
      output: {
        // 在 UMD 构建模式下为这些外部化的依赖提供一个全局变量
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
  },
});