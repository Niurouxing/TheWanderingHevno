// plugins/sandbox_explorer/src/SandboxExplorerPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Typography, CircularProgress } from '@mui/material';

// 导入所有需要的组件
import { SandboxCard } from './components/SandboxCard';
import { CreateSandboxDialog } from './components/CreateSandboxDialog';
import { AddSandboxCard } from './components/AddSandboxCard';

// --- API 调用函数 ---
// 将这些函数放在组件外部，因为它们不依赖于组件状态

/**
 * 从后端获取所有沙盒的列表。
 * @returns {Promise<Array>} 沙盒对象数组
 */
const fetchSandboxes = async () => {
  const response = await fetch('/api/sandboxes');
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch sandboxes: ${errorText}`);
  }
  return response.json();
};

/**
 * 通过上传PNG文件导入一个新的沙盒。
 * @param {File} file - 要上传的PNG文件
 * @returns {Promise<Object>} 新创建的沙盒对象
 */
const importSandbox = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch('/api/sandboxes:import', {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: "Unknown import error" }));
    throw new Error(errData.detail || `Server error: ${response.status}`);
  }
  return response.json();
};

/**
 * 删除一个指定的沙盒。
 * @param {string} sandboxId - 要删除的沙盒ID
 */
const deleteSandbox = async (sandboxId) => {
  const response = await fetch(`/api/sandboxes/${sandboxId}`, {
    method: 'DELETE'
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to delete sandbox: ${errorText}`);
  }
};


// --- 主页面组件 ---

export function SandboxExplorerPage({ services }) {
  // --- 状态管理 ---
  const [sandboxes, setSandboxes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreateDialogOpen, setCreateDialogOpen] = useState(false);
  
  // 从宿主传入的服务中获取 hookManager
  const hookManager = services.get('hookManager');

  // --- 数据加载逻辑 ---
  const loadData = useCallback(async () => {
    // 只有在完全没有数据时才显示全屏加载动画
    if (sandboxes.length === 0) {
      setLoading(true);
    }
    setError('');
    try {
      const data = await fetchSandboxes();
      setSandboxes(data);
    } catch (e) {
      setError(e.message);
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [sandboxes.length]); // 依赖 sandboxes.length 确保只在首次加载时设置全屏loading

  // 在组件首次挂载时加载数据
  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 空依赖数组确保此 effect 只运行一次

  // --- 事件处理函数 ---
  const handleCreate = async (file) => {
    await importSandbox(file);
    await loadData(); // 成功后刷新列表
  };

  const handleDelete = async (sandboxId) => {
    if (window.confirm("Are you sure you want to delete this sandbox? This action cannot be undone.")) {
      try {
        await deleteSandbox(sandboxId);
        await loadData();
      } catch (e) {
          alert(`Error deleting sandbox: ${e.message}`);
          console.error(e);
      }
    }
  };

  const handleSelect = (sandboxId) => {
    // 触发钩子，为未来的编辑器/运行器页面做准备
    hookManager.trigger('sandbox.selected', { sandboxId });
    alert(`Sandbox ${sandboxId} selected! (Hook triggered)`);
  };

  // --- 渲染逻辑 ---
  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
  }

  if (error) {
    return (
        <Box sx={{p: 4, textAlign: 'center'}}>
            <Typography variant="h6" color="error">Failed to load sandboxes</Typography>
            <Typography color="text.secondary">{error}</Typography>
            <Button variant="outlined" sx={{mt: 2}} onClick={loadData}>Try Again</Button>
        </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
      <Typography variant="h4" gutterBottom>My Sandboxes</Typography>
      
      <Grid container spacing={3}>
        {/* 第一项：总是显示添加卡片 */}
        <Grid item xs={12} sm={6} md={4} lg={3}>
          <AddSandboxCard onClick={() => setCreateDialogOpen(true)} />
        </Grid>

        {/* 后续项：渲染已有的沙盒卡片 */}
        {sandboxes.map((sandbox) => (
          <Grid item key={sandbox.id} xs={12} sm={6} md={4} lg={3}>
            <SandboxCard 
                sandbox={sandbox}
                onSelect={handleSelect}
                onEdit={() => alert(`Editing ${sandbox.name}`)}
                onRun={() => alert(`Running ${sandbox.name}`)}
                onDelete={handleDelete}
            />
          </Grid>
        ))}
      </Grid>
      
      <CreateSandboxDialog
        open={isCreateDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCreate={handleCreate}
      />
    </Box>
  );
}

// 默认导出以支持 React.lazy
export default SandboxExplorerPage;