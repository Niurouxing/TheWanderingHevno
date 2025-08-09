// plugins/sandbox_editor/src/SandboxEditorPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, List, ListItem, ListItemText, ListItemIcon, Collapse, IconButton, Button, Switch, TextField, MenuItem, Select, Chip, InputAdornment, Alert } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { useLayout } from '../../core_layout/src/context/LayoutContext';

const SCOPE_TABS = ['definition', 'lore', 'moment'];

const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const isArray = (value) => Array.isArray(value);

// 新组件: Codex 编辑器
function CodexEditor({ sandboxId, scope, codexName, codexData, onBack, onSave }) {
  const [entries, setEntries] = useState(codexData.entries || []);
  const [expanded, setExpanded] = useState({});
  const [editingEntries, setEditingEntries] = useState({}); // 使用对象来跟踪每个条目的编辑状态
  const [errorMessage, setErrorMessage] = useState(''); // For user-visible error messages

  const toggleExpand = (id) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
    // 点击时直接进入编辑模式
    if (!expanded[id]) {
      setEditingEntries((prev) => ({ ...prev, [id]: { ...entries.find(e => e.id === id) } }));
    }
  };

  const handleSaveEntry = async (id) => {
    setErrorMessage(''); // Clear previous error
    const index = entries.findIndex(e => e.id === id);
    if (index === -1) return;

    const originalEntries = [...entries]; // Backup for rollback
    const updatedEntries = [...entries];
    updatedEntries[index] = editingEntries[id];
    setEntries(updatedEntries);
    setEditingEntries((prev) => { const { [id]: _, ...rest } = prev; return rest; });

    // 调用 API 保存
    try {
      const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingEntries[id]),
      });
      if (!response.ok) {
        throw new Error(`Failed to save entry: ${response.statusText}`);
      }
      if (onSave) onSave();
    } catch (e) {
      console.error('Failed to save entry:', e);
      setErrorMessage('Failed to save entry. Please try again.');
      // Rollback UI on failure
      setEntries(originalEntries);
      setEditingEntries((prev) => ({ ...prev, [id]: { ...originalEntries[index] } })); // Re-enter edit mode with original data
    }
  };

  const handleDeleteEntry = async (index, id) => {
    setErrorMessage(''); // Clear previous error
    const originalEntries = [...entries]; // Backup for rollback
    const updatedEntries = entries.filter((_, i) => i !== index);
    setEntries(updatedEntries);

    // 调用 API 删除
    try {
      const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`Failed to delete entry: ${response.statusText}`);
      }
      if (onSave) onSave();
    } catch (e) {
      console.error('Failed to delete entry:', e);
      setErrorMessage('Failed to delete entry. Please try again.');
      setEntries(originalEntries); // Rollback UI on failure
    }
  };

  const handleAddEntry = async () => {
    setErrorMessage(''); // Clear previous error
    const newEntry = {
      id: `entry_${Date.now()}`,
      content: '',
      priority: 100,
      trigger_mode: 'always_on',
      keywords: [],
      is_enabled: true,
    };
    const originalEntries = [...entries]; // Backup for rollback
    const updatedEntries = [...entries, newEntry];
    setEntries(updatedEntries);
    setExpanded((prev) => ({ ...prev, [newEntry.id]: true }));
    setEditingEntries((prev) => ({ ...prev, [newEntry.id]: { ...newEntry } }));

    // 调用 API 添加
    try {
      const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEntry),
      });
      if (!response.ok) {
        throw new Error(`Failed to add entry: ${response.statusText}`);
      }
      if (onSave) onSave();
    } catch (e) {
      console.error('Failed to add entry:', e);
      setErrorMessage('Failed to add entry. Please try again.');
      // Rollback UI on failure
      setEntries(originalEntries);
      setExpanded((prev) => ({ ...prev, [newEntry.id]: false }));
      setEditingEntries((prev) => { const { [newEntry.id]: _, ...rest } = prev; return rest; });
    }
  };

  const handleChange = (id, field, value) => {
    setEditingEntries((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));
  };

  const handleToggleEnabled = async (id, checked) => {
    setErrorMessage(''); // Clear previous error
    const index = entries.findIndex(e => e.id === id);
    if (index === -1) return;

    const originalEntries = [...entries]; // Backup for rollback
    const updatedEntries = [...entries];
    updatedEntries[index].is_enabled = checked;
    setEntries(updatedEntries);

    // 如果在编辑模式，同步到 editingEntries
    if (editingEntries[id]) {
      setEditingEntries((prev) => ({ ...prev, [id]: { ...prev[id], is_enabled: checked } }));
    }

    // 调用 API 更新 enabled
    try {
      const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_enabled: checked }),
      });
      if (!response.ok) {
        throw new Error(`Failed to toggle enabled: ${response.statusText}`);
      }
    } catch (e) {
      console.error('Failed to toggle enabled:', e);
      setErrorMessage('Failed to toggle entry status. Please try again.');
      // Rollback UI on failure
      updatedEntries[index].is_enabled = !checked;
      setEntries(updatedEntries);
      if (editingEntries[id]) {
        setEditingEntries((prev) => ({ ...prev, [id]: { ...prev[id], is_enabled: !checked } }));
      }
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>Editing Codex: {codexName}</Typography>
      <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>Back to Overview</Button>
      <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddEntry} sx={{ mb: 2, ml: 2 }}>Add Entry</Button>
      {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
      <List>
        {entries.map((entry, index) => {
          const editData = editingEntries[entry.id] || entry;

          return (
            <React.Fragment key={entry.id}>
              <ListItem button onClick={() => toggleExpand(entry.id)}>
                <ListItemIcon>
                  {expanded[entry.id] ? <ExpandMoreIcon /> : <ChevronRightIcon />}
                </ListItemIcon>
                <ListItemText
                  primary={entry.id || 'Untitled Entry'}
                  secondary={`Priority: ${entry.priority}`}
                />
                <Switch
                  checked={entry.is_enabled}
                  onChange={(e) => handleToggleEnabled(entry.id, e.target.checked)}
                  onClick={(e) => e.stopPropagation()}
                />
                <IconButton onClick={(e) => { e.stopPropagation(); handleDeleteEntry(index, entry.id); }}>
                  <DeleteIcon />
                </IconButton>
              </ListItem>
              <Collapse in={expanded[entry.id]} timeout="auto" unmountOnExit>
                <Box sx={{ pl: 4, pb: 2 }}>
                  <TextField
                    label="ID"
                    value={editData.id}
                    onChange={(e) => handleChange(entry.id, 'id', e.target.value)}
                    fullWidth
                    sx={{ mb: 2 }}
                  />
                  <TextField
                    label="Content"
                    value={editData.content}
                    onChange={(e) => handleChange(entry.id, 'content', e.target.value)}
                    multiline
                    rows={4}
                    fullWidth
                    sx={{ mb: 2 }}
                  />
                  <TextField
                    label="Priority"
                    type="number"
                    value={editData.priority}
                    onChange={(e) => handleChange(entry.id, 'priority', parseInt(e.target.value))}
                    fullWidth
                    sx={{ mb: 2 }}
                  />
                  <Select
                    value={editData.trigger_mode}
                    onChange={(e) => handleChange(entry.id, 'trigger_mode', e.target.value)}
                    fullWidth
                    sx={{ mb: 2 }}
                  >
                    <MenuItem value="always_on">Always On</MenuItem>
                    <MenuItem value="on_keyword">On Keyword</MenuItem>
                  </Select>
                  {editData.trigger_mode === 'on_keyword' && (
                    <TextField
                      label="Keywords"
                      value={(editData.keywords || []).join(', ')}
                      onChange={(e) => handleChange(entry.id, 'keywords', e.target.value.split(', ').map(k => k.trim()))}
                      fullWidth
                      sx={{ mb: 2 }}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            {(editData.keywords || []).map((kw, i) => <Chip key={i} label={kw} sx={{ mr: 1 }} />)}
                          </InputAdornment>
                        ),
                      }}
                    />
                  )}
                  <Button variant="contained" startIcon={<SaveIcon />} onClick={() => handleSaveEntry(entry.id)} sx={{ mt: 2 }}>
                    Save
                  </Button>
                </Box>
              </Collapse>
            </React.Fragment>
          );
        })}
      </List>
    </Box>
  );
}

// 递归渲染数据的组件，用于显示树状结构
function DataTree({ data, path = '', onEdit, activeScope }) {  // 添加 activeScope 参数
  const [expanded, setExpanded] = useState({});

  const toggleExpand = (key) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (!data) return null;

  return (
    <List disablePadding sx={{ pl: path ? 2 : 0 }}>
      {Object.entries(data).map(([key, value]) => {
        const currentPath = path ? `${path}.${key}` : key;
        const isExpandable = isObject(value) || isArray(value);
        const isCodex = key === 'codices' || (isObject(value) && value.entries && Array.isArray(value.entries));

        return (
          <React.Fragment key={currentPath}>
            <ListItem 
              button 
              onClick={isExpandable ? () => toggleExpand(currentPath) : undefined}
              secondaryAction={
                isCodex ? (
                  <IconButton edge="end" onClick={() => onEdit(currentPath, value, key, activeScope)}>
                    <EditIcon />
                  </IconButton>
                ) : null
              }
            >
              <ListItemIcon>
                {isExpandable ? <FolderIcon /> : <DescriptionIcon />}
              </ListItemIcon>
              <ListItemText 
                primary={key} 
                secondary={
                  !isExpandable 
                    ? (typeof value === 'string' ? value.slice(0, 50) + (value.length > 50 ? '...' : '') : JSON.stringify(value))
                    : `${isArray(value) ? 'Array' : 'Object'} (${Object.keys(value).length} items)`
                } 
              />
              {isExpandable && (
                <IconButton size="small">
                  {expanded[currentPath] ? <ExpandMoreIcon /> : <ChevronRightIcon />}
                </IconButton>
              )}
            </ListItem>
            {isExpandable && (
              <Collapse in={expanded[currentPath]} timeout="auto" unmountOnExit>
                <DataTree data={value} path={currentPath} onEdit={onEdit} activeScope={activeScope} />
              </Collapse>
            )}
          </React.Fragment>
        );
      })}
    </List>
  );
}

export function SandboxEditorPage({ services }) {
  const { currentSandboxId } = useLayout();
  const [sandboxData, setSandboxData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeScope, setActiveScope] = useState(0);
  const [editingCodex, setEditingCodex] = useState(null);

  const loadSandboxData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [definitionRes, loreRes, momentRes] = await Promise.all([
        fetch(`/api/sandboxes/${currentSandboxId}/definition`),
        fetch(`/api/sandboxes/${currentSandboxId}/lore`),
        fetch(`/api/sandboxes/${currentSandboxId}/moment`)
      ]);

      if (!definitionRes.ok || !loreRes.ok || !momentRes.ok) {
        throw new Error('Failed to fetch sandbox scopes');
      }

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
  };

  const handleEdit = (path, value, codexName, activeScopeIndex) => {
    if (value.entries && Array.isArray(value.entries)) {
      let effectiveScope = SCOPE_TABS[activeScopeIndex];
      if (activeScopeIndex === 0) { // 'definition' tab
        const parts = path.split('.');
        if (parts[0] === 'initial_lore') {
          effectiveScope = 'initial_lore';
        } else if (parts[0] === 'initial_moment') {
          effectiveScope = 'initial_moment';
        }
      }
      setEditingCodex({ name: codexName || path.split('.').pop(), data: value, scope: effectiveScope });
    } else {
      console.log(`Editing path: ${path}`, value);
      alert(`Edit functionality for "${path}" is not yet implemented. Value: ${JSON.stringify(value, null, 2)}`);
    }
  };

  const handleBackFromCodex = () => {
    setEditingCodex(null);
    loadSandboxData(); // 刷新数据
  };

  if (!currentSandboxId) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="error">No sandbox selected for editing.</Typography>
      </Box>
    );
  }

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}><CircularProgress /></Box>;
  }

  if (error) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="error">Failed to load sandbox</Typography>
        <Typography color="text.secondary">{error}</Typography>
        <Button variant="outlined" sx={{ mt: 2 }} onClick={loadSandboxData}>Try Again</Button>
      </Box>
    );
  }

  const currentScopeData = sandboxData[SCOPE_TABS[activeScope]];

  if (editingCodex) {
    return (
      <CodexEditor
        sandboxId={currentSandboxId}
        scope={editingCodex.scope}
        codexName={editingCodex.name}
        codexData={editingCodex.data}
        onBack={handleBackFromCodex}
        onSave={loadSandboxData}
      />
    );
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
      <Typography variant="h4" gutterBottom>Editing Sandbox: {currentSandboxId}</Typography>
      
      <Tabs value={activeScope} onChange={handleScopeChange} aria-label="sandbox scopes">
        {SCOPE_TABS.map((scope, index) => (
          <Tab label={scope.charAt(0).toUpperCase() + scope.slice(1)} key={index} />
        ))}
      </Tabs>
      
      <Box sx={{ mt: 2 }}>
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