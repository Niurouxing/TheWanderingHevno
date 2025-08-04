// plugins/sandbox_manager/components/SandboxList.tsx
// [FIXED]

import React, { useCallback, useState } from 'react'; // [FIX] Added useState
import { useApi, services } from '@hevno/frontend-sdk';
import type { Sandbox } from '@hevno/frontend-sdk/types';

// 定义 Sandbox 列表组件
export default function SandboxList() {
  // 1. 使用 useCallback 包装我们的 API 调用函数，这是一个好习惯
  const fetchSandboxes = useCallback(() => {
    return services.api.get<Sandbox[]>('/api/sandboxes');
  }, []);

  // 2. 使用 useApi hook 来获取数据
  const { data: sandboxes, isLoading, error, execute: refetchSandboxes } = useApi(fetchSandboxes);

  // 【新增】用于创建沙盒的API调用状态
  const [isCreating, setIsCreating] = useState(false);

  // 3. 根据状态渲染不同的 UI
  const renderContent = () => {
    if (isLoading) {
      return <p className="text-gray-400">Loading sandboxes...</p>;
    }

    if (error) {
      return <p className="text-red-400">Error: {error.message}</p>;
    }

    if (!sandboxes || sandboxes.length === 0) {
      return <p className="text-gray-500">No sandboxes found.</p>;
    }

    return (
      <ul className="space-y-2">
        {sandboxes.map(sandbox => (
          <li key={sandbox.id} className="p-2 bg-gray-700 rounded hover:bg-gray-600 cursor-pointer">
            <p className="font-semibold text-white">{sandbox.name}</p>
            <p className="text-xs text-gray-400 truncate">{sandbox.id}</p>
          </li>
        ))}
      </ul>
    );
  };

  // 【新增】创建沙盒的函数
  const createNewSandbox = useCallback(async () => {
    const newName = window.prompt("Enter new sandbox name:", "New Sandbox");
    if (!newName) return;

    setIsCreating(true);
    try {
      const newSandboxPayload = {
        name: newName,
        // 根据后端文档，提供一个最小化的图和初始状态
        graph_collection: {
          main: {
            nodes: [
              {
                id: "start",
                run: [{ runtime: "system.io.log", config: { message: "Genesis." } }]
              }
            ]
          }
        },
        initial_state: {}
      };
      // 使用 POST /api/sandboxes 创建
      await services.api.post('/api/sandboxes', newSandboxPayload);
      // 成功后刷新列表
      refetchSandboxes();
    } catch (e) {
      alert(`Failed to create sandbox: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setIsCreating(false);
    }
  }, [refetchSandboxes]);
  
  return (
    <div className="p-2">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-bold text-white">Sandboxes</h3>
        <div className="flex space-x-2">
          <button 
            onClick={createNewSandbox} 
            disabled={isLoading || isCreating}
            className="px-2 py-1 text-xs bg-green-600 rounded hover:bg-green-500 disabled:opacity-50"
          >
            {isCreating ? '...' : '+ New'}
          </button>
          <button 
            onClick={() => refetchSandboxes()} 
            disabled={isLoading || isCreating}
            className="px-2 py-1 text-xs bg-blue-600 rounded hover:bg-blue-500 disabled:opacity-50"
          >
            {isLoading ? '...' : 'Refresh'}
          </button>
        </div>
      </div>
      {renderContent()}
    </div>
  );
}