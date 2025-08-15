// plugins/sandbox_editor/src/editors/RuntimeEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, List, Collapse, IconButton, Button, Select, MenuItem, Typography, Paper, ListSubheader, TextField } from '@mui/material';
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

const NEW_RUNTIME_SYMBOL = Symbol('new_runtime');

export function RuntimeEditor({ runList, onRunListChange }) {
  const [runs, setRuns] = useState(runList || []);
  const [editingRun, setEditingRun] = useState(null);
  const [draftData, setDraftData] = useState(null);

  useEffect(() => {
    setRuns(runList || []);
  }, [runList]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleToggleExpand = (index) => {
    if (editingRun === index) {
      setEditingRun(null);
      setDraftData(null);
    } else {
      setEditingRun(index);
      setDraftData({ ...runs[index] });
    }
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldI = parseInt(active.id, 10);
      const newI = parseInt(over.id, 10);

      const newOrderedRuns = arrayMove(runs, oldI, newI);
      setRuns(newOrderedRuns);
      onRunListChange(newOrderedRuns);
    }
  };

  const handleAddClick = () => {
    if (editingRun !== null) {
      alert("Please save or discard the current runtime first.");
      return;
    }
    setEditingRun(NEW_RUNTIME_SYMBOL);
    setDraftData({ runtime: '', config: {} });
  };
  
  const handleSave = () => {
    if (!draftData.runtime) {
      alert("Runtime type is required.");
      return;
    }
    let newRuns;
    if (editingRun === NEW_RUNTIME_SYMBOL) {
      newRuns = [...runs, draftData];
    } else {
      newRuns = runs.map((run, i) => (i === editingRun ? draftData : run));
    }
    setRuns(newRuns);
    onRunListChange(newRuns);
    
    setEditingRun(null);
    setDraftData(null);
  };

  const handleDelete = (index) => {
    const newRuns = runs.filter((_, i) => i !== index);
    setRuns(newRuns);
    onRunListChange(newRuns);
  };
  
  const handleDiscard = () => {
      setEditingRun(null);
      setDraftData(null);
  }

  const handleDraftChange = (field, value) => {
      setDraftData(prev => ({...prev, [field]: value}));
  }

  const renderRunForm = () => {
    if (!draftData) return null;
    const isNew = editingRun === NEW_RUNTIME_SYMBOL;
    return (
      <Paper sx={{ p: 2, m: 1, border: `1px solid`, borderColor: 'primary.main' }}>
         <Typography variant="h6" sx={{mb: 2}}>{isNew ? "添加指令" : "编辑指令"}</Typography>
        <Select
          value={draftData.runtime}
          onChange={(e) => handleDraftChange('runtime', e.target.value)}
          fullWidth
          size="small"
          displayEmpty
          sx={{ mb: 2 }}
        >
          <MenuItem value="" disabled><em>选择指令类型</em></MenuItem>

          <ListSubheader>LLM</ListSubheader>
          <MenuItem value="llm.default">llm.default</MenuItem>

          <ListSubheader>Memoria</ListSubheader>
          <MenuItem value="memoria.add">memoria.add</MenuItem>
          <MenuItem value="memoria.query">memoria.query</MenuItem>

          <ListSubheader>Codex</ListSubheader>
          <MenuItem value="codex.invoke">codex.invoke</MenuItem>

          <ListSubheader>System IO</ListSubheader>
          <MenuItem value="system.io.input">system.io.input</MenuItem>
          <MenuItem value="system.io.log">system.io.log</MenuItem>

          <ListSubheader>System Data</ListSubheader>
          <MenuItem value="system.data.format">system.data.format</MenuItem>
          <MenuItem value="system.data.parse">system.data.parse</MenuItem>
          <MenuItem value="system.data.regex">system.data.regex</MenuItem>
          
          <ListSubheader>System Flow</ListSubheader>
          <MenuItem value="system.flow.call">system.flow.call</MenuItem>
          <MenuItem value="system.flow.map">system.flow.map</MenuItem>

          <ListSubheader>System Advanced</ListSubheader>
          <MenuItem value="system.execute">system.execute</MenuItem>
        </Select>

        {draftData.runtime && (
          <TextField
            label="as (可选命名空间)"
            value={draftData.config?.as || ''}
            onChange={(e) => {
              const newConfig = { ...draftData.config, as: e.target.value };
              // 如果值为空，则从 config 对象中删除 'as' 键以保持数据清洁
              if (!e.target.value) {
                delete newConfig.as;
              }
              handleDraftChange('config', newConfig);
            }}
            fullWidth
            size="small"
            sx={{ mb: 2 }}
            helperText="为该指令的输出指定一个名称，以便后续指令引用。"
          />
        )}
        
        {draftData.runtime && (
          <RuntimeConfigForm
            runtimeType={draftData.runtime}
            config={draftData.config || {}}
            onConfigChange={(newConfig) => handleDraftChange('config', newConfig)}
          />
        )}
        <Box sx={{mt: 2, display: 'flex', gap: 1}}>
            <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSave}>
                {isNew ? "添加" : "保存"}
            </Button>
            <Button variant="outlined" onClick={handleDiscard}>
                取消
            </Button>
        </Box>
      </Paper>
    );
  };

  return (
    <Paper variant="outlined" sx={{ mt: 2, p:1 }}>
      <Box sx={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <Typography variant="subtitle1" gutterBottom component="div">指令列表</Typography>
        <Button variant="outlined" startIcon={<AddIcon />} onClick={handleAddClick} size="small" sx={{ mb: 1 }} disabled={editingRun !== null}>
            添加指令
        </Button>
      </Box>

      {editingRun !== null ? renderRunForm() : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={runs.map((_, i) => i.toString())} strategy={verticalListSortingStrategy}>
              <List disablePadding>
                {runs.map((run, index) => (
                  <SortableRuntimeItem
                    key={index}
                    id={index.toString()}
                    run={run}
                    onEdit={() => handleToggleExpand(index)}
                    onDelete={() => handleDelete(index)}
                  />
                ))}
                {runs.length === 0 && <Typography color="text.secondary" sx={{p:2, textAlign: 'center'}}>No runtimes defined.</Typography>}
              </List>
            </SortableContext>
          </DndContext>
      )}
    </Paper>
  );
}