// plugins/sandbox_editor/src/editors/CodexEditor.jsx
import React, { useState } from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Button, Switch, TextField, MenuItem, Select, Chip, InputAdornment, Alert } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
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
} from '@dnd-kit/sortable';
import { SortableEntryItem } from '../components/SortableEntryItem';

export function CodexEditor({ sandboxId, scope, codexName, codexData, onBack }) {
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
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ flexShrink: 0 }}>
        <Typography variant="h5" gutterBottom>Editing Codex: {codexName}</Typography>
        <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>Back to Overview</Button>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddEntryClick} sx={{ mb: 2, ml: 2 }}>Add Entry</Button>
        {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
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
    </Box>
  );
}