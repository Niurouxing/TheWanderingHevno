// plugins/sandbox_editor/src/editors/CodexEditor.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, List, Collapse, IconButton, Button, Switch, TextField, MenuItem, Select, Chip, InputAdornment, Alert } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableEntryItem } from '../components/SortableEntryItem';
import { mutate } from '../utils/api';
import { debounce } from '../utils/debounce';

export function CodexEditor({ sandboxId, basePath, codexName, codexData, onBack, confirmationService }) {
  const [entries, setEntries] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [errorMessage, setErrorMessage] = useState('');
  
  useEffect(() => {
    // --- [修复 1/7] 在加载数据时，为每个条目添加一个稳定的内部ID ---
    // 这个ID仅用于UI（React key, DND-kit, 折叠状态），在保存到后端前会被移除。
    const entriesWithInternalIds = (codexData.entries || []).map((entry, index) => ({
        ...entry,
        _internal_id: entry.id + `_${Date.now()}_${index}`
    }));
    setEntries(entriesWithInternalIds);
  }, [codexData]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const syncEntries = async (entriesToSave, optimisticState) => {
    setErrorMessage('');
    setEntries(optimisticState);
    try {
      await mutate(sandboxId, [{
        type: 'UPSERT',
        path: `${basePath}/entries`,
        value: entriesToSave
      }]);
      setEntries(optimisticState);
    } catch (e) {
      setErrorMessage(`Failed to save changes: ${e.message}`);
      throw e;
    }
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = entries.findIndex(e => e._internal_id === active.id);
      const newIndex = entries.findIndex(e => e._internal_id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const reorderedEntries = arrayMove(entries, oldIndex, newIndex);
      const entriesToSave = reorderedEntries.map(({_internal_id, ...rest}) => rest);
      await syncEntries(entriesToSave, reorderedEntries).catch(() => setEntries(entries));
    }
  };

  const handleDelete = async (internalIdToDelete) => {
    const confirmed = await confirmationService.confirm({
      title: '删除条目确认',
      message: '你确定要删除这个条目吗？',
    });
    if (!confirmed) return;
    
    const originalEntries = [...entries];
    const updatedEntries = entries.filter(e => e._internal_id !== internalIdToDelete);
    const entriesToSave = updatedEntries.map(({_internal_id, ...rest}) => rest);
    await syncEntries(entriesToSave, updatedEntries).catch(() => setEntries(originalEntries));
  };
  
  const handleToggleEnabled = async (internalId, is_enabled) => {
    const originalEntries = [...entries];
    const updatedEntries = entries.map(e => e._internal_id === internalId ? { ...e, is_enabled } : e);
    const entryIndex = originalEntries.findIndex(e => e._internal_id === internalId);

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

  const handleAddEntry = async () => {
      const newInternalId = `new_entry_internal_${Date.now()}`;
      const newEntry = {
        _internal_id: newInternalId,
        id: `new_entry_${Date.now()}`, 
        content: '', 
        priority: 100, 
        trigger_mode: 'always_on', 
        keywords: [], 
        is_enabled: true,
      };
      const originalEntries = [...entries];
      const updatedEntries = [...entries, newEntry];
      setExpanded(prev => ({...prev, [newInternalId]: true}));
      
      const entriesToSave = updatedEntries.map(({_internal_id, ...rest}) => rest);
      await syncEntries(entriesToSave, updatedEntries).catch(() => setEntries(originalEntries));
  };

  const debouncedSave = useCallback(debounce(async (updatedEntries) => {
    const entriesToSave = updatedEntries.map(({_internal_id, ...rest}) => rest);
    const originalEntries = [...entries];
    try {
        await syncEntries(entriesToSave, updatedEntries);
    } catch (e) {
        setEntries(originalEntries);
    }
  }, 500), [sandboxId, basePath]);

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

      if (field === 'id' || field === 'content' || field === 'keywords') {
         debouncedSave(updatedEntries);
      } else {
         const entriesToSave = updatedEntries.map(({_internal_id, ...rest}) => rest);
         syncEntries(entriesToSave, updatedEntries).catch(() => setEntries(entries));
      }
  };

  // --- [修复 5/7] 使用 _internal_id 来切换展开状态 ---
  const toggleExpand = (internalId) => {
    setExpanded(prev => ({ ...prev, [internalId]: !prev[internalId] }));
  };

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
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleAddEntry}>
          添加条目
        </Button>
      </Box>
      
      {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}

      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={entries.map(e => e._internal_id)} strategy={verticalListSortingStrategy}>
            <List>
              {entries.map((entry, index) => (
                <SortableEntryItem
                  key={entry._internal_id}
                  id={entry._internal_id}
                  entry={entry}
                  expanded={!!expanded[entry._internal_id]}
                  onToggleExpand={() => toggleExpand(entry._internal_id)}
                  onToggleEnabled={(id, enabled) => handleToggleEnabled(entry._internal_id, enabled)}
                  onDelete={() => handleDelete(entry._internal_id)}
                >
                  <Collapse in={!!expanded[entry._internal_id]} timeout="auto" unmountOnExit>
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