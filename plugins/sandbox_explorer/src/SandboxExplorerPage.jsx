// plugins/sandbox_explorer/src/SandboxExplorerPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Typography, Button, CircularProgress, Fab } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import { SandboxCard } from './components/SandboxCard';
import { CreateSandboxDialog } from './components/CreateSandboxDialog';

// API调用函数
const fetchSandboxes = async () => {
  const response = await fetch('/api/sandboxes');
  if (!response.ok) throw new Error('Failed to fetch sandboxes');
  return response.json();
};

const importSandbox = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch('/api/sandboxes:import', {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
      const errData = await response.json().catch(() => ({detail: "Unknown import error"}));
      throw new Error(errData.detail);
  }
  return response.json();
};

const deleteSandbox = async (sandboxId) => {
    const response = await fetch(`/api/sandboxes/${sandboxId}`, {
        method: 'DELETE'
    });
    if(!response.ok) throw new Error('Failed to delete sandbox');
};

export function SandboxExplorerPage({ services }) {
  const [sandboxes, setSandboxes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreateDialogOpen, setCreateDialogOpen] = useState(false);
  const { hookManager } = services.get('hookManager');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchSandboxes();
      setSandboxes(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async (file) => {
    await importSandbox(file);
    await loadData(); // 成功后刷新列表
  };
  
  const handleDelete = async (sandboxId) => {
      if(window.confirm("Are you sure you want to delete this sandbox? This action cannot be undone.")){
          await deleteSandbox(sandboxId);
          await loadData();
      }
  };

  const handleSelect = (sandboxId) => {
      // 触发钩子，为未来的编辑器/运行器页面做准备
      hookManager.trigger('sandbox.selected', { sandboxId });
      alert(`Sandbox ${sandboxId} selected! (Hook triggered)`);
  };

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  }

  if (error) {
    return <Typography color="error" sx={{ p: 4 }}>Error: {error}</Typography>;
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>My Sandboxes</Typography>
      
      <Grid container spacing={3}>
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

      {sandboxes.length === 0 && !loading && (
          <Typography sx={{mt: 4, textAlign: 'center'}} color="text.secondary">
              You don't have any sandboxes yet. Click the '+' button to import one.
          </Typography>
      )}

      <Fab 
        color="secondary" 
        aria-label="import sandbox"
        sx={{ position: 'absolute', bottom: 32, right: 32 }}
        onClick={() => setCreateDialogOpen(true)}
      >
        <AddIcon />
      </Fab>

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