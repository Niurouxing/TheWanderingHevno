// plugins/sandbox_editor/src/editors/RuntimeEditor.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { Box, List, Collapse, IconButton, Button, Select, MenuItem, Typography, Paper, ListSubheader, TextField } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableRuntimeItem } from '../components/SortableRuntimeItem';
import { RuntimeConfigForm } from './RuntimeConfigForm';
import { getSchemaForRuntime, getAllSchemas } from '../utils/schemaManager';
import { isStringArrayField } from '../components/SchemaField';

export function RuntimeEditor({ runList, onRunListChange }) {
  const [runs, setRuns] = useState(runList || []);
  const [expandedRuns, setExpandedRuns] = useState({});

  const availableRuntimes = useMemo(() => {
    const schemas = getAllSchemas();
    if (!schemas) {
        return { groups: {} };
    }
    const runtimeList = Object.keys(schemas).sort();
    const groups = runtimeList.reduce((acc, name) => {
        const groupName = name.split('.')[0]; 
        if (!acc[groupName]) acc[groupName] = [];
        acc[groupName].push(name);
        return acc;
    }, {});
    return { groups };
  }, []);

  useEffect(() => {
    setRuns(runList || []);
  }, [runList]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleToggleExpand = (index) => {
    const runToExpand = runs[index];
    const originalConfig = runToExpand.config || {};
    const schema = getSchemaForRuntime(runToExpand.runtime);
    const healedConfig = { ...originalConfig };

    if (schema && schema.properties) {
        for (const key in schema.properties) {
            const fieldSchema = schema.properties[key];
            if (isStringArrayField(fieldSchema)) {
                const value = originalConfig[key];
                if (typeof value === 'string') healedConfig[key] = value.split(',').map(s => s.trim()).filter(Boolean);
                else if (value === undefined || value === null) healedConfig[key] = [];
            }
        }
        if (JSON.stringify(healedConfig) !== JSON.stringify(originalConfig)) {
            const newRuns = [...runs];
            newRuns[index] = { ...runToExpand, config: healedConfig };
            setRuns(newRuns);
            onRunListChange(newRuns);
        }
    }
    setExpandedRuns(prev => ({...prev, [index]: !prev[index]}));
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
    const newRuns = [...runs, { runtime: '', config: {} }];
    setRuns(newRuns);
    setExpandedRuns(prev => ({...prev, [newRuns.length - 1]: true }));
  };

  const handleDelete = (index) => {
    const newRuns = runs.filter((_, i) => i !== index);
    setRuns(newRuns);
    onRunListChange(newRuns);
  };
  
  const handleRunChange = (index, updatedRun) => {
    const newRuns = [...runs];
    newRuns[index] = updatedRun;
    setRuns(newRuns);
    onRunListChange(newRuns);
  }

  return (
    <Paper variant="outlined" sx={{ mt: 2, p:1 }}>
      <Box sx={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <Typography variant="subtitle1" gutterBottom component="div">指令列表</Typography>
        <Button variant="outlined" startIcon={<AddIcon />} onClick={handleAddClick} size="small" sx={{ mb: 1 }}>
            添加指令
        </Button>
      </Box>

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
              >
                  <Collapse in={!!expandedRuns[index]}>
                    <Paper sx={{ p: 2, m: 1, border: `1px solid`, borderColor: 'action.disabled' }}>
                        <Select
                            value={run.runtime}
                            onChange={(e) => handleRunChange(index, { ...run, runtime: e.target.value })}
                            fullWidth size="small" displayEmpty sx={{ mb: 2 }}
                        >
                          <MenuItem value="" disabled><em>选择指令类型</em></MenuItem>
                          {Object.entries(availableRuntimes.groups)
                            .sort(([groupA], [groupB]) => groupA.localeCompare(groupB))
                            .map(([groupName, runtimes]) => ([
                                <ListSubheader key={groupName}>{groupName.charAt(0).toUpperCase() + groupName.slice(1)}</ListSubheader>,
                                runtimes.map(runtimeName => <MenuItem key={runtimeName} value={runtimeName}>{runtimeName}</MenuItem>)
                            ]))
                          }
                        </Select>
                        {run.runtime && <TextField label="as (可选命名空间)" value={run.config?.as || ''}
                            onChange={(e) => {
                              const newConfig = { ...run.config, as: e.target.value };
                              if (!e.target.value) delete newConfig.as;
                              handleRunChange(index, { ...run, config: newConfig });
                            }}
                            fullWidth size="small" sx={{ mb: 2 }} helperText="为该指令的输出指定一个名称，以便后续指令引用。"
                          />
                        }
                        {run.runtime && <RuntimeConfigForm
                            runtimeType={run.runtime}
                            schema={getSchemaForRuntime(run.runtime)}
                            config={run.config || {}}
                            onConfigChange={(newConfig) => handleRunChange(index, { ...run, config: newConfig })}
                          />
                        }
                    </Paper>
                  </Collapse>
              </SortableRuntimeItem>
            ))}
            {runs.length === 0 && <Typography color="text.secondary" sx={{p:2, textAlign: 'center'}}>No runtimes defined.</Typography>}
          </List>
        </SortableContext>
      </DndContext>
    </Paper>
  );
}