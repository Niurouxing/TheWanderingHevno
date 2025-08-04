// vite.config.ts (适用于所有插件)
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import dts from 'vite-plugin-dts'; // 建议添加，以生成类型定义

export default defineConfig({
  plugins: [
    react(), // 确保插件内的 React 组件可以正确转换
    dts({ insertTypesEntry: true }) // 生成 d.ts 文件
  ],
  build: {
    // 输出目录
    outDir: 'dist',
    // 开启 sourcemap 用于调试
    sourcemap: true,
    lib: {
      // 插件的入口文件
      entry: path.resolve(__dirname, 'index.ts'),
      // [关键] 构建格式为 IIFE，使其成为一个自执行脚本
      formats: ['iife'],
      // [关键] IIFE 格式需要一个全局变量名，但我们的架构不直接使用它。
      // definePlugin 会处理插件注册，所以这个名字只是一个占位符。
      // 为了避免冲突，我们基于插件名生成一个唯一的 name。
      name: `HevnoPlugin_${path.basename(__dirname)}`,
      // 输出的文件名
      fileName: 'index', 
    },
    rollupOptions: {
      // [关键] 将 react 和 react-dom 设置为外部依赖，不要将它们打包进来
      external: ['react', 'react-dom', '@hevno/frontend-sdk'],
      output: {
        // [关键] 告诉 Rollup，当在代码中遇到这些外部依赖时，
        // 应该去访问的全局变量是什么。
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
          // SDK 也应该通过全局访问，但我们的架构是通过 definePlugin 传递的，
          // 所以这里主要是为了让 Rollup 不报错。
          // 实际上，插件是通过 `import ... from '@hevno/frontend-sdk'` 获得类型，
          // 但在打包时，Vite/Rollup 会因为 `definePlugin` 的存在而进行摇树优化（tree-shaking），
          // 通常不会真的把 SDK 代码打包进去。为保险起见，显式声明。
          '@hevno/frontend-sdk': 'HevnoFrontendSDK' // 假设的全局名，实际上不会使用
        },
      },
    },
  },
});