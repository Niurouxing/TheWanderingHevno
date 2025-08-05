import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    // 使用库模式
    lib: {
      // 库的入口文件
      entry: resolve(__dirname, 'src/main.js'),
      // 库的名称
      name: 'HevnoCoreLayout',
      // 输出的文件名
      fileName: 'main',
      // 输出格式为 ES 模块
      formats: ['es'],
    },
    // 输出目录
    outDir: 'dist',
    // 清空输出目录
    emptyOutDir: true,
    rollupOptions: {
      // 我们不需要将任何外部依赖打包进去
      external: [],
      output: {
        // 全局变量，如果需要的话
        globals: {},
      },
    },
  },
});