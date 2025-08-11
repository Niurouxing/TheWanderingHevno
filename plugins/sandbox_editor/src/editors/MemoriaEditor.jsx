// plugins/sandbox_editor/src/editors/MemoriaEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Button, TextField, Alert, Paper, Chip, InputAdornment } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
// import { SortableMemoryEntryItem } from '../components/SortableMemoryEntryItem'; // 确保你有一个这个组件
import { mutate } from '../utils/api';

// 你需要一个 SortableMemoryEntryItem 组件，这里是一个基本实现
function SortableMemoryEntryItem({ id, entry, children }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : 0,
    position: 'relative',
    listStyle: 'none',
    backgroundColor: isDragging ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
  };
  return (
    <div ref={setNodeRef} style={style}>
      <ListItem sx={{p:0}}>
        <IconButton {...attributes} {...listeners} sx={{ cursor: 'grab', alignSelf: 'flex-start', mt: 3 }}>
          <DragIndicatorIcon />
        </IconButton>
        <Box sx={{width: '100%'}}>{children}</Box>
      </ListItem>
    </div>
  );
}

export function MemoriaEditor({ sandboxId, basePath, memoriaData, onBack }) { 
  const [streams, setStreams] = useState({});
  const [expanded, setExpanded] = useState({});
  const [errorMessage, setErrorMessage] = useState('');
  const [newStreamName, setNewStreamName] = useState('');

  useEffect(() => {
    const initialStreams = {};
    if (memoriaData) {
        Object.entries(memoriaData).forEach(([key, value]) => {
            if (key !== '__hevno_type__' && key !== '__global_sequence__') {
                initialStreams[key] = { ...value, entries: (value.entries || []).map((e, i) => ({ ...e, _internal_id: `${key}_${i}`})) };
            }
        });
    }
    setStreams(initialStreams);
  }, [memoriaData]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleAddStream = async () => {
    if (!newStreamName || newStreamName.trim() === '') {
      setErrorMessage("Stream name is required.");
      return;
    }
    setErrorMessage('');
    try {
      await mutate(sandboxId, [{
        type: 'UPSERT',
        path: `${basePath}/${newStreamName}`,
        value: { entries: [], config: {} },
        mutation_mode: 'DIRECT',
      }]);
      setNewStreamName('');
      onBack(); // 返回并刷新
    } catch (e) {
      setErrorMessage(`Failed to create stream: ${e.message}`);
    }
  };

  const handleDeleteStream = async (streamName) => {
    if (!window.confirm(`Are you sure you want to delete the stream "${streamName}"?`)) return;
    setErrorMessage('');
    try {
      await mutate(sandboxId, [{
        type: 'DELETE',
        path: `${basePath}/${streamName}`,
        mutation_mode: 'DIRECT',
      }]);
      onBack();
    } catch (e) {
      setErrorMessage(`Failed to delete stream: ${e.message}`);
    }
  };

  // 统一的保存函数
  const handleSave = async (streamName, updatedEntries) => {
      const entriesToSave = updatedEntries.map(({_internal_id, ...rest}) => rest); // 移除内部ID
      setErrorMessage('');
      try {
        await mutate(sandboxId, [{
            type: 'UPSERT',
            path: `${basePath}/${streamName}/entries`,
            value: entriesToSave,
            mutation_mode: 'DIRECT',
        }]);
        onBack();
      } catch (e) {
          setErrorMessage(`Failed to save entries for stream ${streamName}: ${e.message}`);
      }
  };
  
  const handleAddEntry = (streamName) => {
      setStreams(prev => {
          const newStreams = {...prev};
          const newEntry = { content: '', level: 'event', tags: [], _internal_id: `${streamName}_${Date.now()}` };
          newStreams[streamName].entries.push(newEntry);
          return newStreams;
      });
  };

  const handleEntryChange = (streamName, entryIndex, field, value) => {
      setStreams(prev => {
          const newStreams = {...prev};
          const entries = [...newStreams[streamName].entries];
          let finalValue = value;
          if (field === 'tags' && typeof value === 'string') {
              finalValue = value.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
          }
          entries[entryIndex] = {...entries[entryIndex], [field]: finalValue};
          newStreams[streamName].entries = entries;
          return newStreams;
      })
  };

  const handleDeleteEntry = (streamName, entryIndex) => {
      setStreams(prev => {
          const newStreams = {...prev};
          newStreams[streamName].entries.splice(entryIndex, 1);
          return newStreams;
      });
  };

  const handleEntryDragEnd = (streamName, event) => {
    const { active, over } = event;
    if (active && over && active.id !== over.id) {
        const stream = streams[streamName];
        if (!stream) return;
        const oldIndex = stream.entries.findIndex(e => e._internal_id === active.id);
        const newIndex = stream.entries.findIndex(e => e._internal_id === over.id);
        if (oldIndex === -1 || newIndex === -1) return;
        const reorderedEntries = arrayMove(stream.entries, oldIndex, newIndex);
        setStreams(prev => ({...prev, [streamName]: {...prev[streamName], entries: reorderedEntries}}));
    }
  };

  const toggleExpand = (key) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const renderEntryForm = (streamName, entry, index) => {
      return (
          <Paper sx={{ p: 2, m:1, border: '1px dashed', borderColor: 'grey.700' }}>
              <TextField label="内容" value={entry.content || ''} onChange={(e) => handleEntryChange(streamName, index, 'content', e.target.value)} multiline fullWidth variant="outlined" sx={{ mb: 2 }} autoFocus />
              <TextField label="级别" value={entry.level || 'event'} onChange={(e) => handleEntryChange(streamName, index, 'level', e.target.value)} fullWidth sx={{ mb: 2 }} size="small" variant="outlined" />
              <TextField label="标签 (逗号分隔)" value={(entry.tags || []).join(', ')} onChange={(e) => handleEntryChange(streamName, index, 'tags', e.target.value)} fullWidth sx={{ mb: 2 }} variant="outlined"
                  InputProps={{
                      startAdornment: (
                          <InputAdornment position="start">
                              {(entry.tags || []).filter(t => t).map((tag, i) => <Chip key={i} label={tag} size="small" sx={{ mr: 0.5 }} />)}
                          </InputAdornment>
                      ),
                  }}
              />
              <Button size="small" variant="outlined" color="error" startIcon={<DeleteIcon/>} onClick={() => handleDeleteEntry(streamName, index)}>删除此条目</Button>
          </Paper>
      );
  };
  
  // --- [修复] 恢复渲染逻辑 ---
  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0 }}>
        <Typography variant="h5" gutterBottom>正在编辑Memoria</Typography>
        <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>返回概览</Button>
        <Paper variant="outlined" sx={{ p: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField label="新Stream名称" value={newStreamName} onChange={e => setNewStreamName(e.target.value)} size="small" />
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddStream}>添加Stream</Button>
        </Paper>
        {errorMessage && <Alert severity="error" sx={{ my: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto', mt: 2 }}>
        <List>
          {Object.entries(streams).map(([streamName, streamData]) => (
            <React.Fragment key={streamName}>
              <Paper sx={{mb: 2, overflow: 'hidden'}} elevation={3}>
                  <ListItem button onClick={() => toggleExpand(streamName)} sx={{backgroundColor: 'rgba(255,255,255,0.05)'}}>
                    <ListItemIcon>{expanded[streamName] ? <ExpandMoreIcon /> : <ChevronRightIcon />}</ListItemIcon>
                    <ListItemText primary={streamName} secondary={`条目数量: ${streamData.entries.length}`} />
                    <Button variant="contained" color="success" size="small" startIcon={<SaveIcon />} sx={{mr: 2}} onClick={(e) => { e.stopPropagation(); handleSave(streamName, streamData.entries); }}>保存此Stream</Button>
                    <IconButton edge="end" onClick={(e) => { e.stopPropagation(); handleDeleteStream(streamName); }}>
                      <DeleteIcon />
                    </IconButton>
                  </ListItem>
                  <Collapse in={expanded[streamName]} timeout="auto" unmountOnExit>
                    <Box sx={{ p: 2 }}>
                      <Button variant="outlined" startIcon={<AddIcon />} onClick={() => handleAddEntry(streamName)} size="small" sx={{ mb: 1 }}>添加条目</Button>
                      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => handleEntryDragEnd(streamName, e)}>
                        <SortableContext items={streamData.entries.map(e => e._internal_id)} strategy={verticalListSortingStrategy}>
                          <List disablePadding>
                            {streamData.entries.map((entry, index) => (
                              <SortableMemoryEntryItem key={entry._internal_id} id={entry._internal_id} entry={entry}>
                                {renderEntryForm(streamName, entry, index)}
                              </SortableMemoryEntryItem>
                            ))}
                          </List>
                        </SortableContext>
                      </DndContext>
                    </Box>
                  </Collapse>
              </Paper>
            </React.Fragment>
          ))}
        </List>
      </Box>
    </Box>
  );
}

