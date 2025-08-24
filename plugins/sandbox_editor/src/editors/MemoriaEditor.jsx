// plugins/sandbox_editor/src/editors/MemoriaEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, List, Collapse, IconButton, Button, TextField, Alert, Chip, InputAdornment,ListItem,ListItemIcon,ListItemText } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';

import { SortableMemoryEntryItem } from '../components/SortableMemoryEntryItem';
import { mutate } from '../utils/api';

export function MemoriaEditor({ sandboxId, basePath, memoriaData, onBack, confirmationService }) {
  const [streams, setStreams] = useState({});
  const [globalSequence, setGlobalSequence] = useState(0);
  const [expandedStreams, setExpandedStreams] = useState({});
  const [expandedEntries, setExpandedEntries] = useState({});
  const [newStreamName, setNewStreamName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!memoriaData) return;
    
    const initialStreams = {};
    Object.entries(memoriaData).forEach(([key, value]) => {
      if (key === '__hevno_type__' || key === '__global_sequence__') {
        if (key === '__global_sequence__') setGlobalSequence(value);
        return;
      }
      const entriesWithInternalIds = (value.entries || []).map((entry, index) => ({
        ...entry,
        _internal_id: `${key}_${entry.id || Date.now()}_${index}`,
      }));
      initialStreams[key] = { ...value, entries: entriesWithInternalIds };
    });
    setStreams(initialStreams);
  }, [memoriaData]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor)
  );
  
  const handleSaveAll = async () => {
    setLoading(true);
    setErrorMessage('');
    const payload = {
      __hevno_type__: 'hevno/memoria',
      __global_sequence__: globalSequence,
    };
    for (const streamName in streams) {
      const stream = streams[streamName];
      payload[streamName] = {
        ...stream,
        entries: stream.entries.map(({ _internal_id, ...rest }) => rest),
      };
    }
    try {
      await mutate(sandboxId, [{ type: 'UPSERT', path: basePath, value: payload }]);
      alert('Memoria saved successfully!');
      onBack();
    } catch (e) {
      setErrorMessage(`Failed to save Memoria: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAddStream = () => {
    const name = newStreamName.trim();
    if (!name || streams[name]) {
      setErrorMessage(name ? `Stream "${name}" already exists.` : "Stream name is required.");
      return;
    }
    setStreams(prev => ({ ...prev, [name]: { config: {}, entries: [] } }));
    setNewStreamName('');
    setExpandedStreams(prev => ({ ...prev, [name]: true }));
  };

  const handleDeleteStream = async (streamName) => {
    if (!confirmationService) {
      console.error('ConfirmationService not available');
      return;
    }
    
    const confirmed = await confirmationService.confirm({
      title: '删除流确认',
      message: `你确定要删除流 "${streamName}" 吗？在保存之前此操作无法撤销。`,
    });
    if (!confirmed) return;
    
    setStreams(prev => {
      const newStreams = { ...prev };
      delete newStreams[streamName];
      return newStreams;
    });
  };

  // 修改 handleAddEntry 以创建完整的 MemoryEntry 对象并更新全局序列号
  const handleAddEntry = (streamName) => {
    // 1. 计算下一个可用的 sequence_id
    const nextSequenceId = globalSequence + 1;

    // 2. 创建一个结构完整的、符合后端 Pydantic 模型的新条目
    const newEntry = {
      // a. 后端必需字段
      id: crypto.randomUUID(), // 使用浏览器内置功能生成唯一ID
      sequence_id: nextSequenceId,
      content: '新记忆条目，请编辑内容。',
      level: 'event',
      tags: [],
      created_at: new Date().toISOString(), // 生成ISO 8601格式的时间戳
      metadata: { source: 'sandbox-editor' },
      
      // b. 仅供前端使用的内部ID，用于React的key和DND-kit
      _internal_id: `entry_internal_${Date.now()}`
    };

    // 3. 更新 streams 状态
    setStreams(prev => {
      const updatedEntries = [...prev[streamName].entries, newEntry];
      return { ...prev, [streamName]: { ...prev[streamName], entries: updatedEntries } };
    });
    
    // 4. 更新全局序列号状态，这至关重要！
    setGlobalSequence(nextSequenceId);

    // 5. 自动展开新创建的条目以便编辑
    setExpandedEntries(exp => ({ ...exp, [newEntry._internal_id]: true }));
  };


  const handleDeleteEntry = (streamName, entryInternalId) => {
    setStreams(prev => {
      const updatedEntries = prev[streamName].entries.filter(e => e._internal_id !== entryInternalId);
      return { ...prev, [streamName]: { ...prev[streamName], entries: updatedEntries } };
    });
  };
  
  const handleEntryChange = (streamName, entryInternalId, field, value) => {
    setStreams(prev => {
      const updatedEntries = prev[streamName].entries.map(entry => {
        if (entry._internal_id === entryInternalId) {
          let finalValue = value;
          if (field === 'tags' && typeof value === 'string') {
            finalValue = value.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
          }
          // [新增] 确保 sequence_id 是数字
          if (field === 'sequence_id') {
              finalValue = parseInt(value, 10) || 0;
          }
          return { ...entry, [field]: finalValue };
        }
        return entry;
      });
      return { ...prev, [streamName]: { ...prev[streamName], entries: updatedEntries } };
    });
  };

  const handleEntryDragEnd = (streamName, event) => {
    const { active, over } = event;
    if (active && over && active.id !== over.id) {
      setStreams(prev => {
        const stream = prev[streamName];
        const oldIndex = stream.entries.findIndex(e => e._internal_id === active.id);
        const newIndex = stream.entries.findIndex(e => e._internal_id === over.id);
        if (oldIndex === -1 || newIndex === -1) return prev;
        const reorderedEntries = arrayMove(stream.entries, oldIndex, newIndex);
        return { ...prev, [streamName]: { ...prev[streamName], entries: reorderedEntries } };
      });
    }
  };

  const toggleStreamExpand = (streamName) => {
    setExpandedStreams(prev => ({ ...prev, [streamName]: !prev[streamName] }));
  };

  const toggleEntryExpand = (entryInternalId) => {
    setExpandedEntries(prev => ({...prev, [entryInternalId]: !prev[entryInternalId] }));
  };
  
  // 更新表单以包含所有可编辑的字段，尤其是 id 和 sequence_id
  const renderEntryForm = (streamName, entry) => (
    <Box sx={{ pl: 9, pr: 2, pb: 2, pt: 1, borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <TextField label="ID (唯一标识)" value={entry.id || ''} onChange={(e) => handleEntryChange(streamName, entry._internal_id, 'id', e.target.value)} fullWidth variant="outlined" size="small" required />
      <TextField label="因果序列号 (Sequence ID)" type="number" value={entry.sequence_id ?? ''} onChange={(e) => handleEntryChange(streamName, entry._internal_id, 'sequence_id', e.target.value)} fullWidth variant="outlined" size="small" required helperText="必须是唯一的、递增的整数"/>
      <TextField label="内容" value={entry.content || ''} onChange={(e) => handleEntryChange(streamName, entry._internal_id, 'content', e.target.value)} multiline fullWidth variant="outlined" autoFocus/>
      <TextField label="级别" value={entry.level || 'event'} onChange={(e) => handleEntryChange(streamName, entry._internal_id, 'level', e.target.value)} fullWidth size="small" variant="outlined"/>
      <TextField label="标签 (逗号分隔)" value={(entry.tags || []).join(', ')} onChange={(e) => handleEntryChange(streamName, entry._internal_id, 'tags', e.target.value)} fullWidth variant="outlined" size="small"
        InputProps={{ startAdornment: (<InputAdornment position="start">{(entry.tags || []).filter(t => t).map((tag, i) => <Chip key={i} label={tag} size="small" sx={{ mr: 0.5 }} />)}</InputAdornment>),}}
      />
    </Box>
  );

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Button variant="outlined" onClick={onBack}>返回概览</Button>
        <Typography variant="h5" component="div" sx={{ flexGrow: 1, m: 0 }}>正在编辑Memoria</Typography>
        <TextField label="新Stream名称" value={newStreamName} onChange={e => setNewStreamName(e.target.value)} size="small" variant="outlined" sx={{ width: '200px' }} />
        <Button variant="outlined" startIcon={<AddIcon />} onClick={handleAddStream}>添加Stream</Button>
        <Button variant="contained" color="success" startIcon={<SaveIcon />} onClick={handleSaveAll} disabled={loading}>{loading ? '正在保存...' : '全部保存'}</Button>
      </Box>
      {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}
      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <List disablePadding>
          {Object.entries(streams).map(([streamName, streamData]) => (
            <React.Fragment key={streamName}>
              <ListItem
                button
                onClick={() => toggleStreamExpand(streamName)}
                sx={{
                  borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
                  backgroundColor: 'transparent',
                  '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.08)' }
                }}
              >
                <ListItemIcon>
                  {expandedStreams[streamName] ? <ExpandMoreIcon /> : <ChevronRightIcon />}
                </ListItemIcon>
                <ListItemText primary={streamName} secondary={`条目数量: ${streamData.entries?.length || 0}`} />
                <IconButton edge="end" onClick={(e) => { e.stopPropagation(); handleDeleteStream(streamName); }}>
                  <DeleteIcon />
                </IconButton>
              </ListItem>
              <Collapse in={!!expandedStreams[streamName]} timeout="auto" unmountOnExit>
                <Box sx={{ pl: 4, pr: 2, pb: 2, pt: 1 }}>
                  <Button variant="outlined" startIcon={<AddIcon />} onClick={() => handleAddEntry(streamName)} size="small" sx={{ mb: 2 }}>添加条目</Button>
                  <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => handleEntryDragEnd(streamName, e)}>
                    <SortableContext items={(streamData.entries || []).map(e => e._internal_id)} strategy={verticalListSortingStrategy}>
                      <List disablePadding>
                        {(streamData.entries || []).map((entry) => (
                          <SortableMemoryEntryItem
                            key={entry._internal_id}
                            id={entry._internal_id}
                            entry={entry}
                            expanded={!!expandedEntries[entry._internal_id]}
                            onToggleExpand={() => toggleEntryExpand(entry._internal_id)}
                            onDelete={() => handleDeleteEntry(streamName, entry._internal_id)}
                          >
                            <Collapse in={!!expandedEntries[entry._internal_id]} timeout="auto" unmountOnExit>
                              {renderEntryForm(streamName, entry)}
                            </Collapse>
                          </SortableMemoryEntryItem>
                        ))}
                      </List>
                    </SortableContext>
                  </DndContext>
                </Box>
              </Collapse>
            </React.Fragment>
          ))}
        </List>
      </Box>
    </Box>
  );
}