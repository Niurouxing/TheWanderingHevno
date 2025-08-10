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
import ArrowBackIcon from '@mui/icons-material/ArrowBack'; 
import DragIndicatorIcon from '@mui/icons-material/DragIndicator'; 
import { useLayout } from '../../core_layout/src/context/LayoutContext';

const SCOPE_TABS = ['definition', 'lore', 'moment'];

const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const isArray = (value) => Array.isArray(value);

// --- 【新增】 导入 dnd-kit ---
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';


function SortableEntryItem({ id, entry, expanded, onToggleExpand, onToggleEnabled, onDelete, children }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : 0,
    position: 'relative',
    backgroundColor: isDragging ? 'rgba(255, 255, 255, 0.1)' : 'transparent'
  };

  return (
    <div ref={setNodeRef} style={style}>
      <ListItem
        button
        onClick={() => onToggleExpand(entry.id)}
        sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab' }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon>
          {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </ListItemIcon>
        <ListItemText primary={entry.id} secondary={`Priority: ${entry.priority}`} />
        <Switch
          checked={entry.is_enabled}
          onChange={(e) => onToggleEnabled(entry.id, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
        />
        <IconButton onClick={(e) => { e.stopPropagation(); onDelete(entry.id); }}>
          <DeleteIcon />
        </IconButton>
      </ListItem>
      {children}
    </div>
  );
}


// --- 重构后的 CodexEditor 组件 ---
function CodexEditor({ sandboxId, scope, codexName, codexData, onBack }) {
  const [entries, setEntries] = useState(codexData.entries || []);
  const [editingEntries, setEditingEntries] = useState({}); // 草稿区, key是原始ID
  const [expanded, setExpanded] = useState({});
  const [newEntryForm, setNewEntryForm] = useState(null); // 独立的新条目表单状态
  const [errorMessage, setErrorMessage] = useState('');
  
  // --- 【新增】 dnd-kit 传感器 ---
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const NEW_ENTRY_KEY = 'new_entry_form';

  const toggleExpand = (originalId) => {
    const isExpanded = !!expanded[originalId];
    setExpanded(prev => ({ ...prev, [originalId]: !isExpanded }));
    if (!isExpanded && !editingEntries[originalId]) {
      const entryToEdit = entries.find(e => e.id === originalId);
      if (entryToEdit) {
        setEditingEntries(prev => ({ ...prev, [originalId]: { ...entryToEdit } }));
      }
    }
  };

  // --- 【新增】 拖拽结束处理函数 ---
  const handleDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = entries.findIndex(e => e.id === active.id);
      const newIndex = entries.findIndex(e => e.id === over.id);
      const newOrderedEntries = arrayMove(entries, oldIndex, newIndex);
      
      // 1. 立即更新UI，提供流畅体验
      setEntries(newOrderedEntries);
      
      // 2. 将新的ID顺序发送到后端
      const entryIds = newOrderedEntries.map(e => e.id);
      try {
        const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries:reorder`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_ids: entryIds }),
        });
        if (!response.ok) {
           throw new Error("Failed to save new order.");
        }
      } catch (e) {
        setErrorMessage(e.message);
        // 如果失败，可以选择回滚UI状态
        setEntries(entries); 
      }
    }
  };

  const handleSave = async (formKey) => {
    setErrorMessage('');
    const isNew = formKey === NEW_ENTRY_KEY;
    const draftData = isNew ? newEntryForm : editingEntries[formKey];

    if (!draftData.id || draftData.id.trim() === '') {
      setErrorMessage("ID is required.");
      return;
    }
    
    if (isNew) {
      try {
        const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draftData)
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: "Failed to create entry." }));
          throw new Error(err.detail);
        }
        const savedEntry = await response.json();
        setEntries(prev => [...prev, savedEntry]);
        setNewEntryForm(null);
      } catch (e) {
        setErrorMessage(e.message);
      }
      return;
    }

    const originalId = formKey;
    const idHasChanged = originalId !== draftData.id;

    if (idHasChanged) {
      try {
        const createResponse = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draftData)
        });
        if (!createResponse.ok) {
          const err = await createResponse.json().catch(() => ({ detail: "Failed to create new entry for rename." }));
          throw new Error(err.detail);
        }
        const createdEntry = await createResponse.json();

        await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${originalId}`, { method: 'DELETE' });
        
        setEntries(prev => [...prev.filter(e => e.id !== originalId), createdEntry]);
        setEditingEntries(prev => { const { [originalId]: _, ...rest } = prev; return rest; });
        setExpanded(prev => { const { [originalId]: _, ...rest } = prev; return rest; });
      } catch (e) {
        setErrorMessage(e.message);
      }
    } else {
      try {
        const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${originalId}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draftData)
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: "Failed to update entry." }));
          throw new Error(err.detail);
        }
        setEntries(prev => prev.map(e => e.id === originalId ? draftData : e));
        setEditingEntries(prev => { const { [originalId]: _, ...rest } = prev; return rest; });
        setExpanded(prev => ({ ...prev, [originalId]: false }));
      } catch (e) {
        setErrorMessage(e.message);
      }
    }
  };

  const handleDelete = async (id) => {
    setErrorMessage('');
    if (id === NEW_ENTRY_KEY) {
      setNewEntryForm(null);
    } else {
      try {
        await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${id}`, { method: 'DELETE' });
        setEntries(prev => prev.filter(e => e.id !== id));
      } catch (e) {
        setErrorMessage("Failed to delete entry.");
      }
    }
  };

  const handleAddEntryClick = () => {
    if (newEntryForm) {
      alert("Please save or discard the current new entry first.");
      return;
    }
    setNewEntryForm({
      id: '', content: '', priority: 100, trigger_mode: 'always_on', keywords: [], is_enabled: true,
    });
  };
  
  const handleChange = (formKey, field, value) => {
    if (formKey === NEW_ENTRY_KEY) {
      setNewEntryForm(prev => ({ ...prev, [field]: value }));
    } else {
      setEditingEntries(prev => ({ ...prev, [formKey]: { ...prev[formKey], [field]: value } }));
    }
  };
  
  const handleToggleEnabled = async (id, checked) => {
    const originalEntry = entries.find(e => e.id === id);
    if (!originalEntry) return;

    const updatedEntry = { ...originalEntry, is_enabled: checked };
    setEntries(prev => prev.map(e => e.id === id ? updatedEntry : e));

    try {
      await fetch(`/api/sandboxes/${sandboxId}/${scope}/codices/${codexName}/entries/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_enabled: checked })
      });
    } catch (e) {
      setErrorMessage("Status update failed; reverting.");
      setEntries(prev => prev.map(e => e.id === id ? originalEntry : e));
    }
  };

  const renderEntryForm = (formKey) => {
    const isNew = formKey === NEW_ENTRY_KEY;
    const data = isNew ? newEntryForm : editingEntries[formKey];
    if (!data) return null;
    return (
        <Box sx={{ pl: 4, pb: 2 }}>
        <TextField
          label="ID"
          value={data.id}
          onChange={(e) => handleChange(formKey, 'id', e.target.value)}
          fullWidth
          sx={{ mt: 2, mb: 2 }}
          autoFocus={isNew}
          placeholder={isNew ? "Enter a unique ID (required)" : ""}
        />
        <TextField
          label="Content"
          value={data.content}
          onChange={(e) => handleChange(formKey, 'content', e.target.value)}
          multiline rows={4} fullWidth sx={{ mb: 2 }}
        />
        <TextField
          label="Priority"
          type="number"
          value={data.priority}
          onChange={(e) => handleChange(formKey, 'priority', parseInt(e.target.value, 10) || 100)}
          fullWidth sx={{ mb: 2 }}
        />
        <Select
          value={data.trigger_mode}
          onChange={(e) => handleChange(formKey, 'trigger_mode', e.target.value)}
          fullWidth sx={{ mb: 2 }}
        >
          <MenuItem value="always_on">Always On</MenuItem>
          <MenuItem value="on_keyword">On Keyword</MenuItem>
        </Select>
        {data.trigger_mode === 'on_keyword' && (
          <TextField
            label="Keywords"
            value={(data.keywords || []).join(', ')}
            onChange={(e) => handleChange(formKey, 'keywords', e.target.value.split(',').map(k => k.trim()))}
            fullWidth sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  {(data.keywords || []).filter(k => k).map((kw, i) => <Chip key={i} label={kw} sx={{ mr: 1 }} />)}
                </InputAdornment>
              ),
            }}
          />
        )}
        <Button variant="contained" startIcon={<SaveIcon />} onClick={() => handleSave(formKey)} sx={{ mt: 2 }}>
          Save
        </Button>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>Editing Codex: {codexName}</Typography>
      <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>Back to Overview</Button>
      <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddEntryClick} sx={{ mb: 2, ml: 2 }}>Add Entry</Button>
      {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={entries.map(e => e.id)} strategy={verticalListSortingStrategy}>
          <List>
            {entries.map((entry) => (
              <SortableEntryItem
                key={entry.id}
                id={entry.id}
                entry={entry}
                expanded={!!expanded[entry.id]}
                onToggleExpand={toggleExpand}
                onToggleEnabled={handleToggleEnabled}
                onDelete={handleDelete}
              >
                <Collapse in={!!expanded[entry.id]} timeout="auto" unmountOnExit>
                  {renderEntryForm(entry.id)}
                </Collapse>
              </SortableEntryItem>
            ))}
          </List>
        </SortableContext>
      </DndContext>

      {newEntryForm && (
        <React.Fragment key={NEW_ENTRY_KEY}>
          <ListItem sx={{ bgcolor: 'action.hover', borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}>
            <ListItemIcon><ExpandMoreIcon /></ListItemIcon>
            <ListItemText primary="New Entry (Unsaved)" />
            <IconButton onClick={() => handleDelete(NEW_ENTRY_KEY)}>
              <DeleteIcon />
            </IconButton>
          </ListItem>
          <Collapse in={true} timeout="auto">
            {renderEntryForm(NEW_ENTRY_KEY)}
          </Collapse>
        </React.Fragment>
      )}
    </Box>
  );
}

// 递归渲染数据的组件，用于显示树状结构
function DataTree({ data, path = '', onEdit, activeScope }) {
  const [expanded, setExpanded] = useState({});
  const toggleExpand = (key) => { setExpanded((prev) => ({ ...prev, [key]: !prev[key] })); };
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
              secondaryAction={isCodex ? (<IconButton edge="end" onClick={() => onEdit(currentPath, value, key, activeScope)}><EditIcon /></IconButton>) : null}
            >
              <ListItemIcon>{isExpandable ? <FolderIcon /> : <DescriptionIcon />}</ListItemIcon>
              <ListItemText 
                primary={key} 
                secondary={!isExpandable ? (typeof value === 'string' ? value.slice(0, 50) + (value.length > 50 ? '...' : '') : JSON.stringify(value)) : `${isArray(value) ? 'Array' : 'Object'} (${Object.keys(value).length} items)`} 
              />
              {isExpandable && (<IconButton size="small" onClick={() => toggleExpand(currentPath)}>{expanded[currentPath] ? <ExpandMoreIcon /> : <ChevronRightIcon />}</IconButton>)}
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