// plugins/sandbox_editor/src/editors/GraphEditor.jsx
import React, { useState } from 'react';
import { Box, Typography, List, Collapse, IconButton, Button, TextField, Select, MenuItem, Alert, Chip, InputAdornment } from '@mui/material';
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
import { SortableNodeItem } from '../components/SortableNodeItem';
import { RuntimeEditor } from './RuntimeEditor';

export function GraphEditor({ sandboxId, scope, graphName, graphData, onBack }) {
  const [nodes, setNodes] = useState(graphData.nodes || []);
  const [editingNodes, setEditingNodes] = useState({}); // 草稿区 for nodes, key是原始ID
  const [expandedNodes, setExpandedNodes] = useState({});
  const [newNodeForm, setNewNodeForm] = useState(null); // 新节点表单
  const [errorMessage, setErrorMessage] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const NEW_NODE_KEY = 'new_node_form';

  const toggleNodeExpand = (originalId) => {
    const isExpanded = !!expandedNodes[originalId];
    setExpandedNodes(prev => ({ ...prev, [originalId]: !isExpanded }));
    if (!isExpanded && !editingNodes[originalId]) {
      const nodeToEdit = nodes.find(n => n.id === originalId);
      if (nodeToEdit) {
        setEditingNodes(prev => ({ ...prev, [originalId]: { ...nodeToEdit, run: [...(nodeToEdit.run || [])] } }));
      }
    }
  };

  const handleNodeDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over.id) {
      const oldIndex = nodes.findIndex(n => n.id === active.id);
      const newIndex = nodes.findIndex(n => n.id === over.id);
      const newOrderedNodes = arrayMove(nodes, oldIndex, newIndex);
      setNodes(newOrderedNodes);
      // TODO: 发送到后端 /api/sandboxes/{sandboxId}/{scope}/graphs/{graphName}/nodes:reorder
      // body: { node_ids: newOrderedNodes.map(n => n.id) }
    }
  };

  const handleAddNodeClick = () => {
    if (newNodeForm) {
      alert("Please save or discard the current new node first.");
      return;
    }
    setNewNodeForm({
      id: '', depends_on: [], run: [], metadata: {}
    });
  };

  const handleNodeSave = async (formKey) => {
    setErrorMessage('');
    const isNew = formKey === NEW_NODE_KEY;
    const draftData = isNew ? newNodeForm : editingNodes[formKey];

    if (!draftData.id || draftData.id.trim() === '') {
      setErrorMessage("Node ID is required.");
      return;
    }

    // TODO: 发送到后端
    // 如果 isNew: POST /api/sandboxes/{sandboxId}/{scope}/graphs/{graphName}/nodes
    // 否则: PUT /api/sandboxes/{sandboxId}/{scope}/graphs/{graphName}/nodes/{originalId}
    // body: draftData
    // 如果 id 变化: 先 POST 新节点，然后 DELETE 旧节点

    if (isNew) {
      // 模拟成功
      setNodes(prev => [...prev, draftData]);
      setNewNodeForm(null);
    } else {
      const originalId = formKey;
      setNodes(prev => prev.map(n => n.id === originalId ? draftData : n));
      setEditingNodes(prev => { const { [originalId]: _, ...rest } = prev; return rest; });
      setExpandedNodes(prev => ({ ...prev, [originalId]: false }));
    }
  };

  const handleNodeDelete = async (id) => {
    setErrorMessage('');
    if (id === NEW_NODE_KEY) {
      setNewNodeForm(null);
    } else {
      // TODO: DELETE /api/sandboxes/{sandboxId}/{scope}/graphs/{graphName}/nodes/{id}
      setNodes(prev => prev.filter(n => n.id !== id));
    }
  };

  const handleNodeChange = (formKey, field, value) => {
    if (formKey === NEW_NODE_KEY) {
      setNewNodeForm(prev => ({ ...prev, [field]: value }));
    } else {
      setEditingNodes(prev => ({ ...prev, [formKey]: { ...prev[formKey], [field]: value } }));
    }
  };

  const renderNodeForm = (formKey) => {
    const isNew = formKey === NEW_NODE_KEY;
    const data = isNew ? newNodeForm : editingNodes[formKey];
    if (!data) return null;
    return (
      <Box sx={{ pl: 4, pb: 2 }}>
        <TextField
          label="Node ID"
          value={data.id}
          onChange={(e) => handleNodeChange(formKey, 'id', e.target.value)}
          fullWidth
          sx={{ mt: 2, mb: 2 }}
          autoFocus={isNew}
          placeholder={isNew ? "Enter a unique ID (required)" : ""}
        />
        <TextField
          label="Depends On (comma-separated IDs)"
          value={(data.depends_on || []).join(', ')}
          onChange={(e) => handleNodeChange(formKey, 'depends_on', e.target.value.split(',').map(id => id.trim()))}
          fullWidth
          sx={{ mb: 2 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                {(data.depends_on || []).filter(id => id).map((id, i) => <Chip key={i} label={id} sx={{ mr: 1 }} />)}
              </InputAdornment>
            ),
          }}
        />
        {/* 二级: Runtime 列表编辑器 */}
        <RuntimeEditor
          runList={data.run || []}
          onRunListChange={(newRun) => handleNodeChange(formKey, 'run', newRun)}
          sandboxId={sandboxId}
          scope={scope}
          graphName={graphName}
          nodeId={data.id} // 用于后端API，如果需要
        />
        <Button variant="contained" startIcon={<SaveIcon />} onClick={() => handleNodeSave(formKey)} sx={{ mt: 2 }}>
          Save Node
        </Button>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>Editing Graph: {graphName}</Typography>
      <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>Back to Overview</Button>
      <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddNodeClick} sx={{ mb: 2, ml: 2 }}>Add Node</Button>
      {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleNodeDragEnd}>
        <SortableContext items={nodes.map(n => n.id)} strategy={verticalListSortingStrategy}>
          <List>
            {nodes.map((node) => (
              <SortableNodeItem
                key={node.id}
                id={node.id}
                node={node}
                expanded={!!expandedNodes[node.id]}
                onToggleExpand={toggleNodeExpand}
                onDelete={handleNodeDelete}
              >
                <Collapse in={!!expandedNodes[node.id]} timeout="auto" unmountOnExit>
                  {renderNodeForm(node.id)}
                </Collapse>
              </SortableNodeItem>
            ))}
          </List>
        </SortableContext>
      </DndContext>

      {newNodeForm && (
        <React.Fragment key={NEW_NODE_KEY}>
          <ListItem sx={{ bgcolor: 'action.hover', borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}>
            <ListItemIcon><ExpandMoreIcon /></ListItemIcon>
            <ListItemText primary="New Node (Unsaved)" />
            <IconButton onClick={() => handleNodeDelete(NEW_NODE_KEY)}>
              <DeleteIcon />
            </IconButton>
          </ListItem>
          <Collapse in={true} timeout="auto">
            {renderNodeForm(NEW_NODE_KEY)}
          </Collapse>
        </React.Fragment>
      )}
    </Box>
  );
}