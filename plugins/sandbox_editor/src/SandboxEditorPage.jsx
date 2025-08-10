import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Button } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SCOPE_TABS } from './utils/constants';
import { DataTree } from './components/DataTree';
import { CodexEditor } from './editors/CodexEditor';

export function SandboxEditorPage({ services }) {
  // --- [修改 1/4] 从 LayoutContext 中获取 setActivePageId 和 setCurrentSandboxId ---
  const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
  const [sandboxData, setSandboxData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeScope, setActiveScope] = useState(0);
  const [editingCodex, setEditingCodex] = useState(null);

  const loadSandboxData = useCallback(async () => {
    if (!currentSandboxId) return;
    setLoading(true);
    setError('');
    try {
      const [definitionRes, loreRes, momentRes] = await Promise.all([
        fetch(`/api/sandboxes/${currentSandboxId}/definition`),
        fetch(`/api/sandboxes/${currentSandboxId}/lore`),
        fetch(`/api/sandboxes/${currentSandboxId}/moment`)
      ]);
      if (!definitionRes.ok || !loreRes.ok || !momentRes.ok) throw new Error('Failed to fetch sandbox scopes');
      const definition = await definitionRes.json();
      const lore = await loreRes.json();
      const moment = await momentRes.json();
      setSandboxData({ definition, lore, moment });
    } catch (e) {
      setError(e.message);
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [currentSandboxId]);

  useEffect(() => {
    if (currentSandboxId) {
      loadSandboxData();
    }
  }, [currentSandboxId, loadSandboxData]);

  const handleScopeChange = (event, newValue) => {
    setActiveScope(newValue);
    setEditingCodex(null);
  };
  
  // --- [新增 2/4] 添加返回按钮的点击处理函数 ---
  const handleGoBackToExplorer = () => {
    setCurrentSandboxId(null); // 清理上下文
    setActivePageId('sandbox_explorer.main_view'); // 切换页面
  };

  const handleEdit = (path, value, codexName, activeScopeIndex) => {
    if (value.entries && Array.isArray(value.entries)) {
      let effectiveScope = SCOPE_TABS[activeScopeIndex];
      if (activeScopeIndex === 0) {
        const parts = path.split('.');
        if (parts[0] === 'initial_lore') effectiveScope = 'initial_lore';
        else if (parts[0] === 'initial_moment') effectiveScope = 'initial_moment';
      }
      setEditingCodex({ name: codexName || path.split('.').pop(), data: value, scope: effectiveScope });
    } else {
      alert(`Edit functionality for "${path}" is not yet implemented.`);
    }
  };

  const handleBackFromCodex = () => {
    setEditingCodex(null);
    loadSandboxData();
  };

  if (!currentSandboxId) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="error">No sandbox selected for editing.</Typography>
      </Box>
    );
  }
  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
  if (error) return (
    <Box sx={{ p: 4, textAlign: 'center' }}>
      <Typography variant="h6" color="error">Failed to load sandbox</Typography>
      <Typography color="text.secondary">{error}</Typography>
      <Button variant="outlined" sx={{ mt: 2 }} onClick={loadSandboxData}>Try Again</Button>
    </Box>
  );

  const currentScopeData = sandboxData[SCOPE_TABS[activeScope]];

  if (editingCodex) {
    return (
      <CodexEditor
        sandboxId={currentSandboxId}
        scope={editingCodex.scope}
        codexName={editingCodex.name}
        codexData={editingCodex.data}
        onBack={handleBackFromCodex}
      />
    );
  }

  return (
    <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* --- [修改 3/4] 重新组织标题区域，添加返回按钮 --- */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, flexShrink: 0 }}>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={handleGoBackToExplorer}
          sx={{ mr: 2 }}
        >
          Back to Explorer
        </Button>
        <Typography variant="h4" component="h1" noWrap sx={{ flexGrow: 1 }}>
          Editing: {sandboxData?.name || 'Sandbox'}
        </Typography>
      </Box>

      {/* --- [修改 4/4] 调整布局，使内容区可滚动 --- */}
      <Tabs value={activeScope} onChange={handleScopeChange} aria-label="sandbox scopes" sx={{ flexShrink: 0, borderBottom: 1, borderColor: 'divider' }}>
        {SCOPE_TABS.map((scope, index) => (
          <Tab label={scope.charAt(0).toUpperCase() + scope.slice(1)} key={index} />
        ))}
      </Tabs>
      <Box sx={{ mt: 2, flexGrow: 1, overflowY: 'auto' }}>
        {currentScopeData ? (
          <DataTree data={currentScopeData} onEdit={(path, value, codexName) => handleEdit(path, value, codexName, activeScope)} activeScope={activeScope} />
        ) : (
          <Typography color="text.secondary">No data available for this scope.</Typography>
        )}
      </Box>
    </Box>
  );
}

export default SandboxEditorPage;