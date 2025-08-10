// plugins/sandbox_editor/src/editors/GraphEditor.jsx
import React, { useState, useRef, useEffect } from 'react'; // --- [MODIFIED] Import useRef and useEffect
import { Box, Typography, List, Collapse, IconButton, Button, TextField, Alert, Chip, InputAdornment } from '@mui/material';
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
    const [editingNodes, setEditingNodes] = useState({});
    const [expandedNodes, setExpandedNodes] = useState({});
    const [newNodeForm, setNewNodeForm] = useState(null);
    const [errorMessage, setErrorMessage] = useState('');

    // --- [NEW] Create a ref for the new node form container ---
    const newNodeFormRef = useRef(null);

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    const NEW_NODE_KEY = 'new_node_form';

    // --- [NEW] Add an effect to scroll to the new form when it appears ---
    useEffect(() => {
        if (newNodeForm && newNodeFormRef.current) {
            newNodeFormRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [newNodeForm]);

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
            if (oldIndex === -1 || newIndex === -1) return;

            const newOrderedNodes = arrayMove(nodes, oldIndex, newIndex);
            setNodes(newOrderedNodes); // Optimistic UI update

            try {
                const nodeIds = newOrderedNodes.map(n => n.id);
                const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/graphs/${graphName}/nodes:reorder`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ node_ids: nodeIds }),
                });
                if (!response.ok) {
                    throw new Error('Failed to save new node order.');
                }
            } catch (e) {
                setErrorMessage(e.message);
                setNodes(nodes); // Revert on failure
            }
        }
    };

    const handleAddNodeClick = () => {
        if (newNodeForm) {
            alert("Please save or discard the current new node first.");
            return;
        }
        setNewNodeForm({ id: '', depends_on: [], run: [], metadata: {} });
    };

    const handleNodeSave = async (formKey) => {
        setErrorMessage('');
        const isNew = formKey === NEW_NODE_KEY;
        const draftData = isNew ? newNodeForm : editingNodes[formKey];

        if (!draftData.id || draftData.id.trim() === '') {
            setErrorMessage("Node ID is required.");
            return;
        }

        if (isNew) {
            try {
                const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/graphs/${graphName}/nodes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(draftData),
                });
                if (!response.ok) {
                    const err = await response.json().catch(() => ({ detail: "Failed to create node." }));
                    throw new Error(err.detail);
                }
                const savedNode = await response.json();
                setNodes(prev => [...prev, savedNode]);
                setNewNodeForm(null);
            } catch (e) {
                setErrorMessage(e.message);
            }
            return;
        }

        const originalId = formKey;
        const idHasChanged = originalId !== draftData.id;

        if (idHasChanged) {
            try {
                const createResponse = await fetch(`/api/sandboxes/${sandboxId}/${scope}/graphs/${graphName}/nodes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(draftData),
                });
                if (!createResponse.ok) throw new Error("Failed to create new node for rename.");
                const createdNode = await createResponse.json();

                await fetch(`/api/sandboxes/${sandboxId}/${scope}/graphs/${graphName}/nodes/${originalId}`, { method: 'DELETE' });

                setNodes(prev => [...prev.filter(n => n.id !== originalId), createdNode]);
                setEditingNodes(prev => { const { [originalId]: _, ...rest } = prev; return rest; });
                setExpandedNodes(prev => ({ ...prev, [originalId]: false }));

            } catch (e) {
                setErrorMessage(e.message);
            }
        } else {
            try {
                const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/graphs/${graphName}/nodes/${originalId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(draftData),
                });
                if (!response.ok) throw new Error("Failed to update node.");

                setNodes(prev => prev.map(n => (n.id === originalId ? draftData : n)));
                setEditingNodes(prev => { const { [originalId]: _, ...rest } = prev; return rest; });
                setExpandedNodes(prev => ({ ...prev, [originalId]: false }));
            } catch (e) {
                setErrorMessage(e.message);
            }
        }
    };

    const handleNodeDelete = async (id) => {
        setErrorMessage('');
        if (id === NEW_NODE_KEY) {
            setNewNodeForm(null);
        } else {
            if (!window.confirm(`Are you sure you want to delete node "${id}"?`)) return;
            try {
                const response = await fetch(`/api/sandboxes/${sandboxId}/${scope}/graphs/${graphName}/nodes/${id}`, { method: 'DELETE' });
                if (!response.ok) throw new Error("Failed to delete node from server.");
                setNodes(prev => prev.filter(n => n.id !== id));
            } catch (e) {
                setErrorMessage(e.message);
            }
        }
    };

    const handleNodeChange = (formKey, field, value) => {
        const updater = (prev) => ({ ...prev, [field]: value });
        if (formKey === NEW_NODE_KEY) {
            setNewNodeForm(updater);
        } else {
            setEditingNodes(prev => ({ ...prev, [formKey]: updater(prev[formKey]) }));
        }
    };

    const renderNodeForm = (formKey) => {
        const isNew = formKey === NEW_NODE_KEY;
        const data = isNew ? newNodeForm : editingNodes[formKey];
        if (!data) return null;
        return (
            <Box sx={{ pl: 4, pb: 2, border: '1px solid rgba(255,255,255,0.2)', borderRadius: 1, m: 1 }}>
                <TextField
                    label="节点ID"
                    value={data.id}
                    onChange={(e) => handleNodeChange(formKey, 'id', e.target.value)}
                    fullWidth
                    sx={{ mt: 2, mb: 2 }}
                    placeholder="必须唯一且非空"
                    autoFocus={isNew}
                />
                <TextField
                    label="依赖于（逗号分隔的ID）"
                    value={(data.depends_on || []).join(', ')}
                    onChange={(e) => handleNodeChange(formKey, 'depends_on', e.target.value.split(',').map(id => id.trim()).filter(Boolean))}
                    fullWidth
                    sx={{ mb: 2 }}
                    placeholder="一般留空"
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                {(data.depends_on || []).filter(id => id).map((id, i) => <Chip key={i} label={id} sx={{ mr: 1 }} />)}
                            </InputAdornment>
                        ),
                    }}
                />
                <RuntimeEditor
                    runList={data.run || []}
                    onRunListChange={(newRunList) => handleNodeChange(formKey, 'run', newRunList)}
                />
                <Button variant="contained" startIcon={<SaveIcon />} onClick={() => handleNodeSave(formKey)} sx={{ mt: 2 }}>
                    {isNew ? "添加节点" : "保存节点"}
                </Button>
            </Box>
        );
    };

    return (
        <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ flexShrink: 0 }}>
                <Typography variant="h5" gutterBottom>正在编辑Graph: {graphName}</Typography>
                <Button variant="outlined" onClick={onBack} sx={{ mb: 2 }}>返回概览</Button>
                <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddNodeClick} sx={{ mb: 2, ml: 2 }}>添加节点</Button>
                {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}
            </Box>

            <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleNodeDragEnd}>
                    <SortableContext items={nodes.map(n => n.id)} strategy={verticalListSortingStrategy}>
                        <List>
                            {nodes.map((node) => (
                                <SortableNodeItem
                                    key={node.id}
                                    id={node.id}
                                    node={node}
                                    expanded={!!expandedNodes[node.id]}
                                    onToggleExpand={() => toggleNodeExpand(node.id)}
                                    onDelete={() => handleNodeDelete(node.id)}
                                >
                                    <Collapse in={!!expandedNodes[node.id]} timeout="auto" unmountOnExit>
                                        {renderNodeForm(node.id)}
                                    </Collapse>
                                </SortableNodeItem>
                            ))}
                        </List>
                    </SortableContext>
                </DndContext>

                {/* --- [MODIFIED] Wrapped the new form in a div and attached the ref --- */}
                <div ref={newNodeFormRef}>
                    {newNodeForm && (
                        <React.Fragment key={NEW_NODE_KEY}>
                            <Collapse in={true} timeout="auto">
                                {renderNodeForm(NEW_NODE_KEY)}
                            </Collapse>
                        </React.Fragment>
                    )}
                </div>
            </Box>
        </Box>
    );
}