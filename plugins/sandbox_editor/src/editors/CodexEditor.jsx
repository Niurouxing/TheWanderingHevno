// plugins/sandbox_editor/src/editors/CodexEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, List, ListItem, ListItemText, ListItemIcon, Collapse, IconButton, Button, Switch, TextField, MenuItem, Select, Chip, InputAdornment, Alert } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableEntryItem } from '../components/SortableEntryItem';
import { mutate } from '../utils/api';

export function CodexEditor({ sandboxId, basePath, codexName, codexData, onBack }) {
  const [entries, setEntries] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [errorMessage, setErrorMessage] = useState('');
  
  useEffect(() => {
    setEntries(codexData.entries || []);
  }, [codexData]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const syncEntries = async (updatedEntries, optimisticState) => {
    setErrorMessage('');
    // 乐观更新UI
    setEntries(optimisticState || updatedEntries);
    try {
      await mutate(sandboxId, [{
        type: 'UPSERT',
        path: `${basePath}/entries`,
        value: updatedEntries
      }]);
      // 确认最终状态
      setEntries(updatedEntries);
    } catch (e) {
      setErrorMessage(`Failed to save changes: ${e.message}`);
      // 如果失败，回滚到操作前的状态
      setEntries(entries);
    }
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = entries.findIndex(e => e.id === active.id);
      const newIndex = entries.findIndex(e => e.id === over.id);
      const reorderedEntries = arrayMove(entries, oldIndex, newIndex);
      await syncEntries(reorderedEntries, reorderedEntries);
    }
  };

  const handleDelete = async (idToDelete) => {
    if (!window.confirm(`Are you sure you want to delete entry "${idToDelete}"?`)) return;
    const updatedEntries = entries.filter(e => e.id !== idToDelete);
    await syncEntries(updatedEntries, updatedEntries);
  };
  
  const handleToggleEnabled = async (id, is_enabled) => {
    const originalEntries = [...entries];
    const updatedEntries = entries.map(e => e.id === id ? { ...e, is_enabled } : e);
    const entryIndex = originalEntries.findIndex(e => e.id === id);

    if (entryIndex === -1) return;
    
    setEntries(updatedEntries); // 乐观更新
    
    setErrorMessage('');
    try {
        await mutate(sandboxId, [{
            type: 'UPSERT',
            path: `${basePath}/entries/${entryIndex}/is_enabled`,
            value: is_enabled,
        }]);
    } catch (e) {
        setErrorMessage(`Status update failed: ${e.message}`);
        setEntries(originalEntries); // 回滚
    }
  };

  const handleAddEntry = () => {
      const newId = `new_entry_${Date.now()}`;
      const newEntry = {
        id: newId, content: '', priority: 100, trigger_mode: 'always_on', keywords: [], is_enabled: true,
      };
      const updatedEntries = [...entries, newEntry];
      setEntries(updatedEntries);
      // 新增条目后自动展开
      setExpanded(prev => ({...prev, [newId]: true}));
  };

  const handleSaveAll = async () => {
    const ids = new Set();
    for (const entry of entries) {
      if (!entry.id || entry.id.trim() === '') {
        setErrorMessage(`Error: An entry has an empty ID.`);
        return;
      }
      if (ids.has(entry.id)) {
        setErrorMessage(`Error: Duplicate ID "${entry.id}" found.`);
        return;
      }
      ids.add(entry.id);
    }
    await syncEntries(entries);
    alert('All changes saved!');
  };
  
  const handleEntryChange = (index, field, value) => {
      const updatedEntries = [...entries];
      const entry = updatedEntries[index];
      
      let finalValue = value;
      if (field === 'priority') {
          finalValue = parseInt(value, 10) || 0;
      } else if (field === 'keywords' && typeof value === 'string') {
          finalValue = value.split(',').map(k => k.trim()).filter(Boolean);
      }
      
      updatedEntries[index] = { ...entry, [field]: finalValue };
      setEntries(updatedEntries);
  };

  const toggleExpand = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // --- [修复] 恢复渲染逻辑 ---
  const renderEntryForm = (entry, index) => {
    return (
        <Box sx={{ pl: 9, pr: 2, pb: 2, pt: 1, borderTop: '1px solid rgba(255,255,255,0.1)'}}>
            <TextField label="ID" value={entry.id} onChange={(e) => handleEntryChange(index, 'id', e.target.value)} fullWidth sx={{ mt: 2, mb: 2 }} required />
            <TextField label="内容" value={entry.content || ''} onChange={(e) => handleEntryChange(index, 'content', e.target.value)} multiline fullWidth sx={{ mb: 2 }} />
            <TextField label="顺序" type="number" value={entry.priority} onChange={(e) => handleEntryChange(index, 'priority', e.target.value)} fullWidth sx={{ mb: 2 }} />
            <Select value={entry.trigger_mode} onChange={(e) => handleEntryChange(index, 'trigger_mode', e.target.value)} fullWidth sx={{ mb: 2 }}>
                <MenuItem value="always_on">常亮</MenuItem>
                <MenuItem value="on_keyword">按关键字触发</MenuItem>
            </Select>
            {entry.trigger_mode === 'on_keyword' && (
                <TextField label="关键词 (逗号分隔)" value={(entry.keywords || []).join(', ')} onChange={(e) => handleEntryChange(index, 'keywords', e.target.value)} fullWidth sx={{ mb: 2 }}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                {(entry.keywords || []).filter(k => k).map((kw, i) => <Chip key={i} label={kw} size="small" sx={{ mr: 0.5 }} />)}
                            </InputAdornment>
                        ),
                    }}
                />
            )}
        </Box>
    );
  };

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Button variant="outlined" onClick={onBack}>返回概览</Button>
        <Typography variant="h5" gutterBottom component="div" sx={{flexGrow: 1, m: 0}}>
          正在编辑Codex: {codexName}
        </Typography>
        <Button variant="outlined" color="primary" startIcon={<AddIcon />} onClick={handleAddEntry}>
          添加条目
        </Button>
        <Button variant="contained" color="success" startIcon={<SaveIcon />} onClick={handleSaveAll}>
          全部保存
        </Button>
      </Box>
      
      {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}

      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={entries.map(e => e.id)} strategy={verticalListSortingStrategy}>
            <List>
              {entries.map((entry, index) => (
                <SortableEntryItem
                  key={entry.id}
                  id={entry.id}
                  entry={entry}
                  expanded={!!expanded[entry.id]}
                  onToggleExpand={() => toggleExpand(entry.id)}
                  onToggleEnabled={handleToggleEnabled}
                  onDelete={() => handleDelete(entry.id)}
                >
                  <Collapse in={!!expanded[entry.id]} timeout="auto" unmountOnExit>
                    {renderEntryForm(entry, index)}
                  </Collapse>
                </SortableEntryItem>
              ))}
            </List>
          </SortableContext>
        </DndContext>
      </Box>
    </Box>
  );
}