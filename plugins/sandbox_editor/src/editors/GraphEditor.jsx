// plugins/sandbox_editor/src/editors/GraphEditor.jsx
import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, List, Collapse, IconButton, Button, TextField, Alert, Chip, InputAdornment } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import SaveIcon from '@mui/icons-material/Save';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableNodeItem } from '../components/SortableNodeItem';
import { RuntimeEditor } from './RuntimeEditor';
import { mutate } from '../utils/api';

export function GraphEditor({ sandboxId, basePath, graphName, graphData, onBack }) {
    const [nodes, setNodes] = useState([]);
    const [expandedNodes, setExpandedNodes] = useState({});
    const [errorMessage, setErrorMessage] = useState('');
    const newNodeFormRef = useRef(null);

    useEffect(() => {
        setNodes(graphData.nodes || []);
    }, [graphData]);

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    const syncNodes = async (updatedNodes, optimisticState) => {
        setErrorMessage('');
        setNodes(optimisticState || updatedNodes); // 乐观更新
        try {
            await mutate(sandboxId, [{
                type: 'UPSERT',
                path: `${basePath}/nodes`,
                value: updatedNodes,
            }]);
            setNodes(updatedNodes); // 确认最终状态
        } catch (e) {
            setErrorMessage(`Failed to save graph changes: ${e.message}`);
            setNodes(nodes); // 回滚
        }
    };
    
    const handleNodeDragEnd = async (event) => {
        const { active, over } = event;
        if (active.id !== over.id) {
            const oldIndex = nodes.findIndex(n => n.id === active.id);
            const newIndex = nodes.findIndex(n => n.id === over.id);
            const reorderedNodes = arrayMove(nodes, oldIndex, newIndex);
            await syncNodes(reorderedNodes, reorderedNodes);
        }
    };
    
    const handleSaveAllNodes = async () => {
        const ids = new Set();
        for (const node of nodes) {
            if (!node.id || node.id.trim() === '') {
                setErrorMessage(`Error: A node has an empty ID.`);
                return;
            }
            if (ids.has(node.id)) {
                setErrorMessage(`Error: Duplicate node ID "${node.id}" found.`);
                return;
            }
            ids.add(node.id);
        }
        await syncNodes(nodes);
        alert('Graph saved!');
    };
    
    const handleDeleteNode = async (idToDelete) => {
        if (!window.confirm(`Are you sure you want to delete node "${idToDelete}"?`)) return;
        const updatedNodes = nodes.filter(n => n.id !== idToDelete);
        await syncNodes(updatedNodes, updatedNodes);
    };

    const handleAddNode = () => {
        const newNode = { id: `new_node_${Date.now()}`, depends_on: [], run: [], metadata: {} };
        setNodes(prev => [...prev, newNode]);
        setExpandedNodes(prev => ({...prev, [newNode.id]: true}));
        setTimeout(() => {
             newNodeFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 100)
    };
    
    const handleNodeChange = (index, field, value) => {
        const updatedNodes = [...nodes];
        let finalValue = value;
        if (field === 'depends_on' && typeof value === 'string') {
            finalValue = value.split(',').map(id => id.trim()).filter(Boolean)
        }
        updatedNodes[index] = { ...updatedNodes[index], [field]: finalValue };
        setNodes(updatedNodes);
    };

    const toggleNodeExpand = (id) => {
        setExpandedNodes(prev => ({ ...prev, [id]: !prev[id] }));
    };

    // ---恢复渲染逻辑 ---
    const renderNodeForm = (node, index) => {
        return (
            <Box sx={{ pl: 9, pr: 2, pb: 2, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <TextField label="节点ID" value={node.id} onChange={(e) => handleNodeChange(index, 'id', e.target.value)} fullWidth sx={{ mt: 2, mb: 2 }} required />
                <TextField label="依赖于 (逗号分隔的ID)" value={(node.depends_on || []).join(', ')} onChange={(e) => handleNodeChange(index, 'depends_on', e.target.value)} fullWidth sx={{ mb: 2 }}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                {(node.depends_on || []).filter(id => id).map((id, i) => <Chip key={i} label={id} size="small" sx={{ mr: 0.5 }} />)}
                            </InputAdornment>
                        ),
                    }}
                />
                <RuntimeEditor
                    runList={node.run || []}
                    onRunListChange={(newRunList) => handleNodeChange(index, 'run', newRunList)}
                />
            </Box>
        );
    };

    return (
        <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Button variant="outlined" onClick={onBack}>返回概览</Button>
                <Typography variant="h5" component="div" sx={{flexGrow: 1}}>正在编辑Graph: {graphName}</Typography>
                <Button variant="outlined" startIcon={<AddIcon />} onClick={handleAddNode}>添加节点</Button>
                <Button variant="contained" color="success" startIcon={<SaveIcon />} onClick={handleSaveAllNodes}>全部保存</Button>
            </Box>
            {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}

            <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleNodeDragEnd}>
                    <SortableContext items={nodes.map(n => n.id)} strategy={verticalListSortingStrategy}>
                        <List>
                            {nodes.map((node, index) => (
                                <div key={node.id} ref={index === nodes.length -1 ? newNodeFormRef : null}>
                                    <SortableNodeItem
                                        id={node.id}
                                        node={node}
                                        expanded={!!expandedNodes[node.id]}
                                        onToggleExpand={() => toggleNodeExpand(node.id)}
                                        onDelete={() => handleDeleteNode(node.id)}
                                    >
                                        <Collapse in={!!expandedNodes[node.id]} timeout="auto" unmountOnExit>
                                            {renderNodeForm(node, index)}
                                        </Collapse>
                                    </SortableNodeItem>
                                </div>
                            ))}
                        </List>
                    </SortableContext>
                </DndContext>
            </Box>
        </Box>
    );
}