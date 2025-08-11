// plugins/sandbox_explorer/src/SandboxExplorerPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Typography, CircularProgress, Button } from '@mui/material';

import { SandboxCard } from './components/SandboxCard';
import { AddSandboxDialog } from './components/AddSandboxDialog';
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

// --- 新增的 API 调用函数 ---
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

  const handleRun = (sandboxId) => {
    setCurrentSandboxId(sandboxId);
    setActivePageId('runner_ui.main_view');
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
      
      <Grid container spacing={3}>
        <Grid >
          <AddSandboxCard onClick={() => setAddDialogOpen(true)} />
        </Grid>

        {sandboxes.map((sandbox) => (
          <Grid key={sandbox.id} >
            <SandboxCard 
                sandbox={sandbox}
                onSelect={handleSelect}
                onEdit={() => handleEdit(sandbox.id)}
                onRun={() => handleRun(sandbox.id)}
                onDelete={handleDelete}
                onExportPng={() => handleExport(sandbox.id, sandbox.name, 'png')}
                onExportJson={() => handleExport(sandbox.id, sandbox.name, 'json')}
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