// plugins/sandbox_editor/src/SandboxEditorPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, List, ListItem, ListItemText, ListItemIcon, Collapse, IconButton, Button } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import FolderIcon from '@mui/icons-material/Folder';
import DescriptionIcon from '@mui/icons-material/Description';
import EditIcon from '@mui/icons-material/Edit';
import { useLayout } from '../../core_layout/src/context/LayoutContext';

const SCOPE_TABS = ['definition', 'lore', 'moment'];

const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const isArray = (value) => Array.isArray(value);

// 递归渲染数据的组件，用于显示树状结构
function DataTree({ data, path = '', onEdit }) {
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
        const isEditableType = ['graphs', 'codices', 'memoria'].includes(key) || 
          (isObject(value) && (value.nodes || value.entries)); // 检测单个graph/codex/memoria

        return (
          <React.Fragment key={currentPath}>
            <ListItem 
              button 
              onClick={isExpandable ? () => toggleExpand(currentPath) : undefined}
              secondaryAction={
                isEditableType ? (
                  <IconButton edge="end" onClick={() => onEdit(currentPath, value)}>
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
                <DataTree data={value} path={currentPath} onEdit={onEdit} />
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

  const handleEdit = (path, value) => {
    // 暂时留空：未来在这里导航到具体的编辑页面，或打开模态框编辑单个graph/codex/memoria
    console.log(`Editing path: ${path}`, value);
    alert(`Edit functionality for "${path}" is not yet implemented. Value: ${JSON.stringify(value, null, 2)}`);
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
          <DataTree data={currentScopeData} onEdit={handleEdit} />
        ) : (
          <Typography color="text.secondary">No data available for this scope.</Typography>
        )}
      </Box>
    </Box>
  );
}

export default SandboxEditorPage;