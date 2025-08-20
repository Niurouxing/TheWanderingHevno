// plugins/sandbox_explorer/src/SandboxExplorerPage.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Grid, Typography, CircularProgress, Button } from '@mui/material';

import { SandboxCard } from './components/SandboxCard';
import { AddSandboxDialog } from './components/AddSandboxDialog';
import { AddSandboxCard } from './components/AddSandboxCard';

// --- API 调用函数 ---

const fetchSandboxes = async () => {
  const response = await fetch('/api/sandboxes');
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch sandboxes: ${errorText}`);
  }
  return response.json();
};

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

const importSandboxFromJson = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
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

const createEmptySandbox = async (name) => {
  const response = await fetch('/api/sandboxes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: "Unknown create error" }));
    throw new Error(errData.detail || `Server error: ${response.status}`);
  }
  return response.json();
};

// ---上传沙盒图标的API函数 ---
const uploadSandboxIcon = async (sandboxId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`/api/sandboxes/${sandboxId}/icon`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: "封面上传失败" }));
    throw new Error(errData.detail || `Server error: ${response.status}`);
  }
  return response.json();
};


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
  const [isAddDialogOpen, setAddDialogOpen] = useState(false);
  
  // [新增] 从services获取useLayout钩子
  const useLayout = services.get('useLayout');
  if (!useLayout) {
    // 优雅降级：如果未注册，抛出错误或使用默认值
    console.error('[sandbox_explorer] useLayout hook not found in services.');
    return <Box sx={{ p: 4, color: 'error.main' }}>错误：核心布局服务不可用。</Box>;
  }
  const { setActivePageId, setCurrentSandboxId } = useLayout();
  
  const hookManager = services.get('hookManager');
  const confirmationService = services?.get('confirmationService');


  const loadData = useCallback(async () => {
    setLoading(true); // 总是在开始加载时设置为 true
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
  }, []); // 依赖项数组置空，确保函数实例在组件生命周期内保持稳定

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleImport = async (file) => {
    if (file.type === 'application/json' || file.name.endsWith('.json')) {
      await importSandboxFromJson(file);
    } else if (file.type === 'image/png') {
      await importSandboxFromPng(file);
    } else {
      throw new Error('Unsupported file type.');
    }
    await loadData();
  };

  const handleCreateEmpty = async (name) => {
    await createEmptySandbox(name);
    await loadData();
  };

  const handleDelete = async (sandboxId) => {
    if (!confirmationService) {
      console.error('ConfirmationService not available');
      return;
    }
    
    const confirmed = await confirmationService.confirm({
      title: '删除沙盒确认',
      message: '你确定要删除这个沙盒吗？此操作不可撤销。',
    });
    if (!confirmed) return;
    
    try {
      await deleteSandbox(sandboxId);
      await loadData();
    } catch (e) {
        alert(`删除沙盒时出错: ${e.message}`);
        console.error(e);
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
      alert(`导出沙盒时出错: ${e.message}`);
      console.error(e);
    }
  };

  const handleSelect = (sandboxId) => {
    hookManager.trigger('sandbox.selected', { sandboxId });
    alert(`已选择沙盒 ${sandboxId}！ (钩子已触发)`);
  };

  const handleEdit = (sandboxId) => {
    setCurrentSandboxId(sandboxId);
    setActivePageId('sandbox_editor.main_view');
  };

  const handleRun = (sandboxId) => {
    setCurrentSandboxId(sandboxId);
    setActivePageId('runner_ui.main_view');
  };
  
  // ---  处理图标上传的函数 ---
  const handleUploadIcon = async (sandboxId, file) => {
    try {
        // 调用新创建的API函数
        await uploadSandboxIcon(sandboxId, file);
        // 此处调用 loadData 现在将始终获取最新数据并刷新UI
        await loadData();
    } catch (e) {
        alert(`上传封面失败: ${e.message}`);
        console.error(e);
    }
  };


  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
  }

  if (error) {
    return (
        <Box sx={{p: 4, textAlign: 'center'}}>
            <Typography variant="h6" color="error">加载沙盒失败</Typography>
            <Typography color="text.secondary">{error}</Typography>
            <Button variant="outlined" sx={{mt: 2}} onClick={loadData}>重试</Button>
        </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
      <Typography variant="h4" gutterBottom>沙盒</Typography>
      
      {/* [修复] 3. 为 Grid 组件添加 'item' prop，符合MUI的最佳实践 */}
      <Grid container spacing={3}>
        <Grid item>
          <AddSandboxCard onClick={() => setAddDialogOpen(true)} />
        </Grid>

        {sandboxes.map((sandbox) => (
          <Grid item key={sandbox.id} >
            <SandboxCard 
                sandbox={sandbox}
                onSelect={handleSelect}
                onEdit={() => handleEdit(sandbox.id)}
                onRun={() => handleRun(sandbox.id)}
                onDelete={handleDelete}
                onExportPng={() => handleExport(sandbox.id, sandbox.name, 'png')}
                onExportJson={() => handleExport(sandbox.id, sandbox.name, 'json')}
                onUploadIcon={handleUploadIcon}
            />
          </Grid>
        ))}
      </Grid>
      
      <AddSandboxDialog
        open={isAddDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        onImport={handleImport}
        onCreateEmpty={handleCreateEmpty}
      />
    </Box>
  );
}

export default SandboxExplorerPage;