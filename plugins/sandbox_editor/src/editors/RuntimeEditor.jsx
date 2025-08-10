// plugins/sandbox_editor/src/editors/RuntimeEditor.jsx
// 这是一个子组件，用于编辑单个节点内的 run 列表 (二级列表)
import React, { useState } from 'react';
import { Box, List, ListItem, ListItemIcon, ListItemText, Collapse, IconButton, Button, Select, MenuItem,Typography } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
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
import { SortableRuntimeItem } from '../components/SortableRuntimeItem';
import { RuntimeConfigForm } from './RuntimeConfigForm';

export function RuntimeEditor({ runList, onRunListChange, sandboxId, scope, graphName, nodeId }) {
  const [runs, setRuns] = useState(runList);
  const [editingRuns, setEditingRuns] = useState({}); // 草稿区 for individual run items, key是 index (stringified)
  const [expandedRuns, setExpandedRuns] = useState({});
  const [newRunFormIndex, setNewRunFormIndex] = useState(null); // 新 runtime 的临时索引

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const toggleRunExpand = (index) => {
    const isExpanded = !!expandedRuns[index];
    setExpandedRuns(prev => ({ ...prev, [index]: !isExpanded }));
    if (!isExpanded && !editingRuns[index]) {
      const runToEdit = runs[index];
      if (runToEdit) {
        setEditingRuns(prev => ({ ...prev, [index]: { ...runToEdit } }));
      }
    }
  };

  const handleRunDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = parseInt(active.id, 10);
      const newIndex = parseInt(over.id, 10);
      const newOrderedRuns = arrayMove(runs, oldIndex, newIndex);
      setRuns(newOrderedRuns);
      onRunListChange(newOrderedRuns);
      // TODO: 如果需要，发送到后端 reorder API
    }
  };

  const handleAddRunClick = () => {
    if (newRunFormIndex !== null) {
      alert("Please save or discard the current new runtime first.");
      return;
    }
    const newIndex = runs.length;
    setNewRunFormIndex(newIndex);
    setEditingRuns(prev => ({ ...prev, [newIndex]: { runtime: '', config: {} } }));
    setExpandedRuns(prev => ({ ...prev, [newIndex]: true }));
  };

  const handleRunSave = (index) => {
    const draftData = editingRuns[index];
    if (!draftData.runtime) {
      alert("Runtime type is required.");
      return;
    }
    const newRuns = [...runs];
    newRuns[index] = draftData;
    setRuns(newRuns);
    onRunListChange(newRuns);
    setEditingRuns(prev => { const { [index]: _, ...rest } = prev; return rest; });
    setExpandedRuns(prev => ({ ...prev, [index]: false }));
    if (index === newRunFormIndex) {
      setNewRunFormIndex(null);
    }
    // TODO: 发送到后端 update API
  };

  const handleRunDelete = (index) => {
    const newRuns = runs.filter((_, i) => i !== index);
    setRuns(newRuns);
    onRunListChange(newRuns);
    // TODO: 发送到后端 delete API
    if (index === newRunFormIndex) {
      setNewRunFormIndex(null);
    }
  };

  const handleRunChange = (index, field, value) => {
    setEditingRuns(prev => ({ ...prev, [index]: { ...prev[index], [field]: value } }));
  };

  const renderRunForm = (index) => {
    const data = editingRuns[index];
    if (!data) return null;
    return (
      <Box sx={{ pl: 4, pb: 2 }}>
        <Select
          value={data.runtime}
          onChange={(e) => handleRunChange(index, 'runtime', e.target.value)}
          fullWidth
          sx={{ mb: 2 }}
          displayEmpty
        >
          <MenuItem value="" disabled>Select Runtime Type</MenuItem>
          {/* TODO: 从文档或后端获取所有可用 runtime 类型 */}
          <MenuItem value="system.io.input">system.io.input</MenuItem>
          <MenuItem value="system.io.log">system.io.log</MenuItem>
          <MenuItem value="system.data.format">system.data.format</MenuItem>
          {/* ... 其他类型 ... */}
        </Select>
        {data.runtime && (
          <RuntimeConfigForm
            runtimeType={data.runtime}
            config={data.config || {}}
            onConfigChange={(newConfig) => handleRunChange(index, 'config', newConfig)}
          />
        )}
        <Button variant="contained" startIcon={<SaveIcon />} onClick={() => handleRunSave(index)} sx={{ mt: 2 }}>
          Save Runtime
        </Button>
      </Box>
    );
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle1" gutterBottom>Runtime Instructions</Typography>
      <Button variant="outlined" startIcon={<AddIcon />} onClick={handleAddRunClick} size="small" sx={{ mb: 1 }}>Add Runtime</Button>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleRunDragEnd}>
        <SortableContext items={runs.map((_, i) => i.toString())} strategy={verticalListSortingStrategy}>
          <List disablePadding>
            {runs.map((run, index) => (
              <SortableRuntimeItem
                key={index}
                id={index.toString()}
                run={run}
                expanded={!!expandedRuns[index]}
                onToggleExpand={() => toggleRunExpand(index)}
                onDelete={() => handleRunDelete(index)}
              >
                <Collapse in={!!expandedRuns[index]} timeout="auto" unmountOnExit>
                  {renderRunForm(index)}
                </Collapse>
              </SortableRuntimeItem>
            ))}
            {newRunFormIndex !== null && (
              <ListItem sx={{ bgcolor: 'action.hover' }}>
                <ListItemIcon><ChevronRightIcon /></ListItemIcon>
                <ListItemText primary="New Runtime (Unsaved)" />
                <IconButton onClick={() => handleRunDelete(newRunFormIndex)}>
                  <DeleteIcon />
                </IconButton>
              </ListItem>
            )}
          </List>
        </SortableContext>
      </DndContext>
    </Box>
  );
}