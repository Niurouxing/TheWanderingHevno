// plugins/sandbox_editor/src/editors/MemoriaEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, List, Collapse, IconButton, Button, TextField, Alert, Chip, InputAdornment } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';

import { SortableMemoryEntryItem } from '../components/SortableStreamItem';
import { mutate } from '../utils/api';
import { SortableStreamItem } from '../components/SortableStreamItem'; // 新组件，类似于 SortableNodeItem

export function MemoriaEditor({ sandboxId, basePath, memoriaData, onBack }) {
  const [streams, setStreams] = useState([]); // 更改为数组 [{name: string, data: {config: {}, entries: []}}]
  const [globalSequence, setGlobalSequence] = useState(0);
  const [expandedStreams, setExpandedStreams] = useState({});
  const [expandedEntries, setExpandedEntries] = useState({});
  const [newStreamName, setNewStreamName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!memoriaData) return;
    
    let gs = 0;
    const initialStreams = Object.entries(memoriaData)
      .filter(([key]) => key !== '__hevno_type__' && key !== '__global_sequence__')
      .map(([name, data]) => {
        if (key === '__global_sequence__') gs = value;
        const entriesWithInternalIds = (data.entries || []).map((entry, index) => ({
          ...entry,
          _internal_id: `${name}_${Date.now()}_${index}`,
        }));
        return { name, data: { ...data, entries: entriesWithInternalIds } };
      });
    setGlobalSequence(gs);
    setStreams(initialStreams);
  }, [memoriaData]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleSaveAll = async () => {
    setLoading(true);
    setErrorMessage('');
    const payload = {
      __hevno_type__: 'hevno/memoria',
      __global_sequence__: globalSequence,
    };
    streams.forEach(({ name, data }) => {
      payload[name] = {
        ...data,
        entries: data.entries.map(({ _internal_id, ...rest }) => rest),
      };
    });
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
    if (!name || streams.some(s => s.name === name)) {
      setErrorMessage(name ? `Stream "${name}" already exists.` : "Stream name is required.");
      return;
    }
    setStreams(prev => [...prev, { name, data: { config: {}, entries: [] } }]);
    setNewStreamName('');
  };

  const handleDeleteStream = (streamName) => {
    if (!window.confirm(`Are you sure you want to delete the stream "${streamName}"? This cannot be undone until you save.`)) return;
    setStreams(prev => prev.filter(s => s.name !== streamName));
  };

  const handleAddEntry = (streamIndex) => {
    setStreams(prev => {
      const newStreams = [...prev];
      const stream = newStreams[streamIndex];
      const newEntry = {
        content: '', level: 'event', tags: [],
        _internal_id: `${stream.name}_${Date.now()}`
      };
      stream.data.entries = [...stream.data.entries, newEntry];
      setExpandedEntries(exp => ({ ...exp, [newEntry._internal_id]: true }));
      return newStreams;
    });
  };

  const handleDeleteEntry = (streamIndex, entryInternalId) => {
    setStreams(prev => {
      const newStreams = [...prev];
      const stream = newStreams[streamIndex];
      stream.data.entries = stream.data.entries.filter(e => e._internal_id !== entryInternalId);
      return newStreams;
    });
  };

  const handleEntryChange = (streamIndex, entryInternalId, field, value) => {
    setStreams(prev => {
      const newStreams = [...prev];
      const stream = newStreams[streamIndex];
      stream.data.entries = stream.data.entries.map(entry => {
        if (entry._internal_id === entryInternalId) {
          let finalValue = value;
          if (field === 'tags' && typeof value === 'string') {
            finalValue = value.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
          }
          return { ...entry, [field]: finalValue };
        }
        return entry;
      });
      return newStreams;
    });
  };

  const handleStreamDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = streams.findIndex(s => s.name === active.id);
      const newIndex = streams.findIndex(s => s.name === over.id);
      const reorderedStreams = arrayMove(streams, oldIndex, newIndex);
      setStreams(reorderedStreams);
    }
  };

  const handleEntryDragEnd = (streamIndex, event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      setStreams(prev => {
        const newStreams = [...prev];
        const stream = newStreams[streamIndex];
        const oldI = stream.data.entries.findIndex(e => e._internal_id === active.id);
        const newI = stream.data.entries.findIndex(e => e._internal_id === over.id);
        if (oldI === -1 || newI === -1) return prev;
        stream.data.entries = arrayMove(stream.data.entries, oldI, newI);
        return newStreams;
      });
    }
  };

  const toggleStreamExpand = (streamName) => {
    setExpandedStreams(prev => ({ ...prev, [streamName]: !prev[streamName] }));
  };

  const toggleEntryExpand = (entryInternalId) => {
    setExpandedEntries(prev => ({...prev, [entryInternalId]: !prev[entryInternalId] }));
  };

  const renderEntryForm = (streamIndex, entry) => (
    <Box sx={{ pl: 9, pr: 2, pb: 2, pt: 1, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
      <TextField label="内容" value={entry.content || ''} onChange={(e) => handleEntryChange(streamIndex, entry._internal_id, 'content', e.target.value)} multiline fullWidth variant="outlined" sx={{ mb: 2 }} autoFocus/>
      <TextField label="级别" value={entry.level || 'event'} onChange={(e) => handleEntryChange(streamIndex, entry._internal_id, 'level', e.target.value)} fullWidth sx={{ mb: 2 }} size="small" variant="outlined"/>
      <TextField label="标签 (逗号分隔)" value={(entry.tags || []).join(', ')} onChange={(e) => handleEntryChange(streamIndex, entry._internal_id, 'tags', e.target.value)} fullWidth sx={{ mb: 2 }} variant="outlined" size="small"
        InputProps={{ startAdornment: (<InputAdornment position="start">{(entry.tags || []).filter(t => t).map((tag, i) => <Chip key={i} label={tag} size="small" sx={{ mr: 0.5 }} />)}</InputAdornment>),}}
      />
    </Box>
  );

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
            <Button variant="outlined" onClick={onBack}>返回概览</Button>
            <Typography variant="h5" component="div" sx={{ flexGrow: 1, m: 0 }}>正在编辑Memoria</Typography>
            <Button variant="contained" color="success" startIcon={<SaveIcon />} onClick={handleSaveAll} disabled={loading}>{loading ? '正在保存...' : '全部保存'}</Button>
        </Box>
        {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2, flexShrink: 0 }}>
            <TextField label="新Stream名称" value={newStreamName} onChange={e => setNewStreamName(e.target.value)} size="small" variant="outlined" fullWidth />
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddStream}>添加Stream</Button>
        </Box>
        <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleStreamDragEnd}>
              <SortableContext items={streams.map(s => s.name)} strategy={verticalListSortingStrategy}>
                <List disablePadding>
                  {streams.map((stream, streamIndex) => (
                    <SortableStreamItem
                      key={stream.name}
                      id={stream.name}
                      stream={stream}
                      expanded={!!expandedStreams[stream.name]}
                      onToggleExpand={() => toggleStreamExpand(stream.name)}
                      onDelete={() => handleDeleteStream(stream.name)}
                    >
                      <Collapse in={!!expandedStreams[stream.name]} timeout="auto" unmountOnExit>
                        <Box sx={{ pl: 4, pr: 2, pb: 2, pt: 1, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                          <Button variant="outlined" startIcon={<AddIcon />} onClick={() => handleAddEntry(streamIndex)} size="small" sx={{ mb: 2 }}>添加条目</Button>
                          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => handleEntryDragEnd(streamIndex, e)}>
                            <SortableContext items={(stream.data.entries || []).map(e => e._internal_id)} strategy={verticalListSortingStrategy}>
                              <List disablePadding>
                                {(stream.data.entries || []).map((entry) => (
                                  <SortableMemoryEntryItem
                                    key={entry._internal_id}
                                    id={entry._internal_id}
                                    entry={entry}
                                    expanded={!!expandedEntries[entry._internal_id]}
                                    onToggleExpand={() => toggleEntryExpand(entry._internal_id)}
                                    onDelete={() => handleDeleteEntry(streamIndex, entry._internal_id)}
                                  >
                                    <Collapse in={!!expandedEntries[entry._internal_id]} timeout="auto" unmountOnExit>
                                      {renderEntryForm(streamIndex, entry)}
                                    </Collapse>
                                  </SortableMemoryEntryItem>
                                ))}
                              </List>
                            </SortableContext>
                          </DndContext>
                        </Box>
                      </Collapse>
                    </SortableStreamItem>
                  ))}
                </List>
              </SortableContext>
            </DndContext>
        </Box>
    </Box>
  );
}