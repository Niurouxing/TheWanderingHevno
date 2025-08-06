// plugins/core_goliath/src/App.jsx (最终无 Shadow DOM 版)

import React from 'react';
// 直接从 dashboard 模板导入根组件
import Dashboard from './dashboard/Dashboard';

export default function App() {
  // 这个组件现在变得极其简单，它只负责渲染 Dashboard
  return (
    <Dashboard />
  );
}