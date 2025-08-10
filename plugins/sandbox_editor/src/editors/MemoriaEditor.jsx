// plugins/sandbox_editor/src/editors/MemoriaEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Button, Switch, TextField, MenuItem, Select, Chip, InputAdornment, Alert, Paper } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
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
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function SortableMemoryEntryItem({ id, entry, expanded, onToggleExpand, onDelete, children }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 1 : 0,
    position: 'relative',
    backgroundColor: isDragging ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
    listStyle: 'none',
  };
  
  const tagsSummary = (entry.tags || []).join(', ');

  return (
    <div ref={setNodeRef} style={style}>
      <ListItem
        button
        onClick={onToggleExpand}
        sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}
        secondaryAction={
            <IconButton edge="end" aria-label="delete" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
              <DeleteIcon />
            </IconButton>
        }
      >
        <ListItemIcon {...attributes} {...listeners} sx={{ cursor: 'grab' }}>
          <DragIndicatorIcon />
        </ListItemIcon>
        <ListItemIcon>
          {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </ListItemIcon>
        <ListItemText 
          primary={<Typography noWrap>{entry.content || '(No Content)'}</Typography>}
          secondary={`ID: ${entry.id} | Level: ${entry.level || 'N/A'}`}
          sx={{ pr: 4 }}
        />
      </ListItem>
      {children}
    </div>
  );
}


export function MemoriaEditor({ sandboxId, memoriaData, onBack }) {
  const [streams, setStreams] = useState({});
  const [editingEntries, setEditingEntries] = useState({});
  const [expanded, setExpanded] = useState({});
  const [newEntryForms, setNewEntryForms] = useState({});
  const [newStreamForm, setNewStreamForm] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const NEW_ENTRY_KEY = 'new_entry_form';

  useEffect(() => {
    const initialStreams = {};
    if (memoriaData) {
        Object.entries(memoriaData).forEach(([key, value]) => {
            if (key !== '__hevno_type__' && key !== '__global_sequence__') {
                initialStreams[key] = { ...value, entries: value.entries || [] };
            }
        });
    }
    setStreams(initialStreams);
  }, [memoriaData]);
  
  const toggleExpand = (key) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleAddStreamClick = () => {
    if (newStreamForm) {
      alert("Please save or discard the current new stream first.");
      return;
    }
    setNewStreamForm({ name: '', entries: [], config: {} });
    setExpanded({ ...expanded, [NEW_ENTRY_KEY]: true });
  };
  
  const handleSaveStream = async () => {
    setErrorMessage('');
    const draftName = newStreamForm.name;
    if (!draftName || draftName.trim() === '') {
      setErrorMessage("Stream name is required.");
      return;
    }
    try {
      // [FIX] 更新 API URL，移除 scope
      const response = await fetch(`/api/sandboxes/${sandboxId}/memoria/${draftName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries: [], config: newStreamForm.config || {} }),
      });
      if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Failed to create stream.' }));
          throw new Error(errData.detail);
      }
      const newStreamData = await response.json();
      setStreams(prev => ({ ...prev, [draftName]: newStreamData }));
      setNewStreamForm(null);
    } catch (e) {
      setErrorMessage(e.message);
    }
  };

  const handleDeleteStream = async (streamName) => {
    if (!window.confirm(`Are you sure you want to delete the stream "${streamName}"? This is irreversible.`)) {
        return;
    }
    setErrorMessage('');
    try {
      // [FIX] 更新 API URL，移除 scope
      const response = await fetch(`/api/sandboxes/${sandboxId}/memoria/${streamName}`, { method: 'DELETE' });
      if (!response.ok) throw new Error("Failed to delete stream from server.");
      setStreams(prev => {
        const { [streamName]: _, ...rest } = prev;
        return rest;
      });
    } catch (e) {
      setErrorMessage(e.message);
    }
  };

  const handleAddEntryClick = (streamName) => {
    if (newEntryForms[streamName]) {
      alert("Please save or discard the current new entry first.");
      return;
    }
    setNewEntryForms(prev => ({ ...prev, [streamName]: {
      content: '', level: 'event', tags: [],
    } }));
    toggleExpand(`${streamName}.${NEW_ENTRY_KEY}`);
  };
  
  const handleCancelNewEntry = (streamName) => {
      setNewEntryForms(prev => {
          const { [streamName]: _, ...rest } = prev;
          return rest;
      });
  };

  const handleEntryChange = (streamName, entryId, field, value) => {
    const isNew = entryId === NEW_ENTRY_KEY;
    const key = `${streamName}.${entryId}`;
    if (isNew) {
      setNewEntryForms(prev => ({ ...prev, [streamName]: { ...prev[streamName], [field]: value } }));
    } else {
      setEditingEntries(prev => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
    }
  };

  const handleSaveEntry = async (streamName, entryId) => {
    setErrorMessage('');
    const isNew = entryId === NEW_ENTRY_KEY;
    const key = `${streamName}.${entryId}`;
    const draftData = isNew ? newEntryForms[streamName] : editingEntries[key];

    if (!draftData || !draftData.content || draftData.content.trim() === '') {
      setErrorMessage("Content is required.");
      return;
    }

    try {
      let savedEntry;
      if (isNew) {
        // [FIX] 更新 API URL，移除 scope
        const response = await fetch(`/api/sandboxes/${sandboxId}/memoria/${streamName}/entries`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draftData)
        });
        if (!response.ok) throw new Error("Failed to create entry.");
        savedEntry = await response.json();
        setStreams(prev => ({
          ...prev,
          [streamName]: { ...prev[streamName], entries: [...prev[streamName].entries, savedEntry] }
        }));
        setNewEntryForms(prev => { const { [streamName]: _, ...rest } = prev; return rest; });
      } else {
        // [FIX] 更新 API URL，移除 scope
        const response = await fetch(`/api/sandboxes/${sandboxId}/memoria/${streamName}/entries/${entryId}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draftData)
        });
        if (!response.ok) throw new Error("Failed to update entry.");
        const updatedEntry = await response.json();
        setStreams(prev => ({
          ...prev,
          [streamName]: {
            ...prev[streamName],
            entries: prev[streamName].entries.map(e => e.id === entryId ? updatedEntry : e)
          }
}));
        setEditingEntries(prev => { const { [key]: _, ...rest } = prev; return rest; });
        toggleExpand(key);
      }
    } catch (e) {
      setErrorMessage(e.message);
    }
  };

  const handleDeleteEntry = async (streamName, entryId) => {
    if (!window.confirm(`Are you sure you want to delete this entry?`)) return;
    setErrorMessage('');
    try {
      // [FIX] 更新 API URL，移除 scope
      await fetch(`/api/sandboxes/${sandboxId}/memoria/${streamName}/entries/${entryId}`, { method: 'DELETE' });
      setStreams(prev => ({
        ...prev,
        [streamName]: { ...prev[streamName], entries: prev[streamName].entries.filter(e => e.id !== entryId) }
      }));
    } catch (e) {
      setErrorMessage("Failed to delete entry.");
    }
  };

  const toggleEntryExpand = (streamName, entryId) => {
    const key = `${streamName}.${entryId}`;
    const isExpanded = !!expanded[key];
    toggleExpand(key);

    if (!isExpanded && !editingEntries[key] && entryId !== NEW_ENTRY_KEY) {
      const entryToEdit = streams[streamName].entries.find(e => e.id === entryId);
      if (entryToEdit) {
        setEditingEntries(prev => ({ ...prev, [key]: { ...entryToEdit } }));
      }
    }
  };

  const handleEntryDragEnd = async (streamName, event) => {
    const { active, over } = event;
    if (active && over && active.id !== over.id) {
      const oldIndex = streams[streamName].entries.findIndex(e => e.id === active.id);
      const newIndex = streams[streamName].entries.findIndex(e => e.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;
      
      const reorderedEntries = arrayMove(streams[streamName].entries, oldIndex, newIndex);
      setStreams(prev => ({ ...prev, [streamName]: { ...prev[streamName], entries: reorderedEntries } }));
      
      try {
        const entryIds = reorderedEntries.map(e => e.id);
        // [FIX] 更新 API URL，移除 scope
        await fetch(`/api/sandboxes/${sandboxId}/memoria/${streamName}/entries:reorder`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_ids: entryIds }),
        });
      } catch (e) {
        setErrorMessage(e.message);
      }
    }
  };
  
    const renderEntryForm = (streamName, entryId) => {
        const isNew = entryId === NEW_ENTRY_KEY;
        const key = `${streamName}.${entryId}`;
        const data = isNew ? newEntryForms[streamName] : editingEntries[key];
        if (!data) return null;

        return (
        <Paper sx={{ pl: 4, pr: 2, pb: 2, pt: 1, m:1, border: '1px dashed', borderColor: 'grey.700' }}>
            <TextField
            label="内容"
            value={data.content || ''}
            onChange={(e) => handleEntryChange(streamName, entryId, 'content', e.target.value)}
            multiline
            fullWidth
            variant="outlined"
            sx={{ mb: 2 }}
            autoFocus
            />
            <TextField
                label="级别"
                value={data.level || 'event'}
                onChange={(e) => handleEntryChange(streamName, entryId, 'level', e.target.value)}
                fullWidth
                sx={{ mb: 2 }}
                size="small"
                variant="outlined"
            />
            <TextField
            label="标签 (逗号分隔)"
            value={(data.tags || []).join(', ')}
            onChange={(e) => handleEntryChange(streamName, entryId, 'tags', e.target.value.split(',').map(t => t.trim().toLowerCase()).filter(Boolean))}
            fullWidth sx={{ mb: 2 }}
            variant="outlined"
            InputProps={{
                startAdornment: (
                <InputAdornment position="start">
                    {(data.tags || []).filter(t => t).map((tag, i) => <Chip key={i} label={tag} size="small" sx={{ mr: 0.5 }} />)}
                </InputAdornment>
                ),
            }}
            />
            <Box>
                <Button variant="contained" startIcon={<SaveIcon />} onClick={() => handleSaveEntry(streamName, entryId)}>
                    保存
                </Button>
                <Button variant="outlined" onClick={() => isNew ? handleCancelNewEntry(streamName) : toggleEntryExpand(streamName, entryId)} sx={{ml: 1}}>
                    取消
                </Button>
            </Box>
        </Paper>
        );
  };


  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0 }}>
        <Typography variant="h5" gutterBottom>正在编辑Memoria</Typography>
        <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>返回概览</Button>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddStreamClick} sx={{ mb: 2, ml: 2 }} disabled={!!newStreamForm}>添加Stream</Button>
        {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        <List>
        {newStreamForm && (
            <Paper sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'primary.main' }}>
                <Typography variant="h6" sx={{mb: 2}}>添加新Stream</Typography>
                <TextField
                label="新Stream名称"
                value={newStreamForm.name}
                onChange={(e) => setNewStreamForm({ ...newStreamForm, name: e.target.value })}
                fullWidth
                sx={{ mb: 2 }}
                autoFocus
                />
                <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSaveStream}>
                    保存Stream
                </Button>
                <Button variant="outlined" onClick={() => setNewStreamForm(null)} sx={{ml: 1}}>
                    取消
                </Button>
            </Paper>
        )}
          {Object.keys(streams).map((streamName) => (
            <React.Fragment key={streamName}>
              <ListItem button onClick={() => toggleExpand(streamName)} sx={{backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 1, mb: 1}}>
                <ListItemIcon>{expanded[streamName] ? <ExpandMoreIcon /> : <ChevronRightIcon />}</ListItemIcon>
                <ListItemText primary={streamName} secondary={`条目数量: ${streams[streamName].entries.length}`} />
                <IconButton edge="end" onClick={(e) => { e.stopPropagation(); handleDeleteStream(streamName); }}>
                  <DeleteIcon />
                </IconButton>
              </ListItem>
              <Collapse in={expanded[streamName]} timeout="auto" unmountOnExit>
                <Box sx={{ pl: 2, pr: 1, pb: 2 }}>
                  <Button variant="outlined" startIcon={<AddIcon />} onClick={() => handleAddEntryClick(streamName)} size="small" sx={{ m: 1 }} disabled={!!newEntryForms[streamName]}>
                    添加条目
                  </Button>
                  <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => handleEntryDragEnd(streamName, e)}>
                    <SortableContext items={streams[streamName].entries.map(e => e.id)} strategy={verticalListSortingStrategy}>
                      <List disablePadding>
                        {streams[streamName].entries.map((entry) => (
                          <SortableMemoryEntryItem
                            key={entry.id}
                            id={entry.id}
                            entry={entry}
                            expanded={!!expanded[`${streamName}.${entry.id}`]}
                            onToggleExpand={() => toggleEntryExpand(streamName, entry.id)}
                            onDelete={() => handleDeleteEntry(streamName, entry.id)}
                          >
                            <Collapse in={!!expanded[`${streamName}.${entry.id}`]} timeout="auto" unmountOnExit>
                              {renderEntryForm(streamName, entry.id)}
                            </Collapse>
                          </SortableMemoryEntryItem>
                        ))}
                      </List>
                    </SortableContext>
                  </DndContext>
                  {newEntryForms[streamName] && (
                    <Collapse in={true} timeout="auto">
                        {renderEntryForm(streamName, NEW_ENTRY_KEY)}
                    </Collapse>
                  )}
                </Box>
              </Collapse>
            </React.Fragment>
          ))}
        </List>
      </Box>
    </Box>
  );
}