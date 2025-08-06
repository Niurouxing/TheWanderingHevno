// plugins/core_goliath/src/App.jsx

import React from 'react';
// 直接从 dashboard 模板导入根组件
import Dashboard from './Dashboard';

// 1. 导入我们新创建的 SandboxProvider
import { SandboxProvider } from './context/SandboxContext';

export default function App() {
  // 2. 用 SandboxProvider 包裹 Dashboard 组件
  return (
    <SandboxProvider>
      <Dashboard />
    </SandboxProvider>
  );
}