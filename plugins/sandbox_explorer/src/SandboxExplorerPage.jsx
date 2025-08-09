// plugins/sandbox_explorer/src/SandboxExplorerPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Typography, CircularProgress, Button } from '@mui/material'; // --- MODIFIED: 导入 Button ---

import { SandboxCard } from './components/SandboxCard';
import { CreateSandboxDialog } from './components/CreateSandboxDialog';
import { AddSandboxCard } from './components/AddSandboxCard';
import { useLayout } from '../../core_layout/src/context/LayoutContext';

// --- API 调用函数 ---

const fetchSandboxes = async () => {
  const response = await fetch('/api/sandboxes');
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch sandboxes: ${errorText}`);
  }
  return response.json();
};

// --- MODIFIED: 重命名为 importSandboxFromPng ---
const importSandboxFromPng = async (file) => {
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

// --- NEW: 添加用于 JSON 导入的 API 函数 ---
const importSandboxFromJson = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  // 使用新的后端端点
  const response = await fetch('/api/sandboxes/import/json', {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: "Unknown import error" }));
    throw new Error(errData.detail || `Server error: ${response.status}`);
  }
  return response.json();
}

// --- NEW: 辅助函数，用于触发浏览器下载 ---
const triggerDownload = async (url, filename) => {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to download file: ${response.statusText}`);
    }
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(link.href);
}

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
  const [sandboxes, setSandboxes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreateDialogOpen, setCreateDialogOpen] = useState(false);
  const { setActivePageId, setCurrentSandboxId } = useLayout();
  
  const hookManager = services.get('hookManager');

  const loadData = useCallback(async () => {
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
  }, [sandboxes.length]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- MODIFIED: 更新 handleCreate 以处理不同文件类型 ---
  const handleCreate = async (file) => {
    // 根据文件类型调用不同的导入函数
    if (file.type === 'application/json' || file.name.endsWith('.json')) {
      console.log('Importing from JSON...');
      await importSandboxFromJson(file);
    } else if (file.type === 'image/png') {
      console.log('Importing from PNG...');
      await importSandboxFromPng(file);
    } else {
      // 这是一个备用检查，理论上在对话框组件中已被阻止
      throw new Error('Unsupported file type.');
    }
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
  
  const handleExport = async (sandboxId, sandboxName, format) => {
    const filename = `${sandboxName.replace(/\s+/g, '_')}_${sandboxId.substring(0,8)}.${format}`;
    const url = format === 'json' 
      ? `/api/sandboxes/${sandboxId}/export/json` 
      : `/api/sandboxes/${sandboxId}/export`;
    try {
      await triggerDownload(url, filename);
    } catch (e) {
      alert(`Error exporting sandbox: ${e.message}`);
      console.error(e);
    }
  };

  const handleSelect = (sandboxId) => {
    hookManager.trigger('sandbox.selected', { sandboxId });
    alert(`Sandbox ${sandboxId} selected! (Hook triggered)`);
  };

  const handleEdit = (sandboxId) => {
    setCurrentSandboxId(sandboxId);
    setActivePageId('sandbox_editor.main_view');
  };

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
        <Grid item xs={12} sm={6} md={4} lg={3}>
          <AddSandboxCard onClick={() => setCreateDialogOpen(true)} />
        </Grid>

        {sandboxes.map((sandbox) => (
          <Grid item key={sandbox.id} xs={12} sm={6} md={4} lg={3}>
            <SandboxCard 
                sandbox={sandbox}
                onSelect={handleSelect}
                onEdit={() => handleEdit(sandbox.id)}
                onRun={() => alert(`Running ${sandbox.name}`)}
                onDelete={handleDelete}
                onExportPng={() => handleExport(sandbox.id, sandbox.name, 'png')}
                onExportJson={() => handleExport(sandbox.id, sandbox.name, 'json')}
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

export default SandboxExplorerPage;