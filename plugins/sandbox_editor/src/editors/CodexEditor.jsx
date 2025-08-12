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
    // 乐观更新UI，使用包含 _internal_id 的状态
    setEntries(optimisticState || entries.map((e, i) => ({...e, _internal_id: entries[i]._internal_id || `temp_${Date.now()}` })));
    try {
      await mutate(sandboxId, [{
        type: 'UPSERT',
        path: `${basePath}/entries`,
        value: entriesToSave // 只保存干净的数据到后端
      }]);
      // 确认最终状态 (如果 optimisticState 提供了，则使用它)
      if (optimisticState) {
          setEntries(optimisticState);
      }
    } catch (e) {
      setErrorMessage(`Failed to save changes: ${e.message}`);
      // 如果失败，回滚到操作前的状态 (此处的 'entries' 是闭包捕获的旧状态)
      setEntries(entries);
    }
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      // --- [修复 2/7] 使用 _internal_id 来查找索引 ---
      const oldIndex = entries.findIndex(e => e._internal_id === active.id);
      const newIndex = entries.findIndex(e => e._internal_id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const reorderedEntries = arrayMove(entries, oldIndex, newIndex);
      // 在保存到后端前，移除内部ID
      const entriesToSave = reorderedEntries.map(({_internal_id, ...rest}) => rest);
      await syncEntries(entriesToSave, reorderedEntries);
    }
  };

  const handleDelete = async (internalIdToDelete) => {
    if (!window.confirm(`Are you sure you want to delete this entry?`)) return;
    // --- [修复 3/7] 使用 _internal_id 进行过滤 ---
    const updatedEntries = entries.filter(e => e._internal_id !== internalIdToDelete);
    const entriesToSave = updatedEntries.map(({_internal_id, ...rest}) => rest);
    await syncEntries(entriesToSave, updatedEntries);
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

  const handleAddEntry = () => {
      // --- [修复 4/7] 添加条目时，同时创建 _internal_id ---
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
      const updatedEntries = [...entries, newEntry];
      setEntries(updatedEntries);
      // 使用 _internal_id 作为 key 来展开
      setExpanded(prev => ({...prev, [newInternalId]: true}));
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
    // 在保存前，移除所有内部ID
    const entriesToSave = entries.map(({_internal_id, ...rest}) => rest);
    await syncEntries(entriesToSave, entries); // 传入乐观状态以保持UI
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
          {/* --- [修复 6/7] 使用 _internal_id 作为 dnd-kit 的 ID 来源 --- */}
          <SortableContext items={entries.map(e => e._internal_id)} strategy={verticalListSortingStrategy}>
            <List>
              {entries.map((entry, index) => (
                // --- [修复 7/7] 使用 _internal_id 作为 React key 和组件的唯一标识 ---
                <SortableEntryItem
                  key={entry._internal_id}
                  id={entry._internal_id}
                  entry={entry}
                  expanded={!!expanded[entry._internal_id]}
                  onToggleExpand={() => toggleExpand(entry._internal_id)}
                  onToggleEnabled={(id, enabled) => handleToggleEnabled(entry._internal_id, enabled)} // 传递内部ID
                  onDelete={() => handleDelete(entry._internal_id)} // 传递内部ID
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