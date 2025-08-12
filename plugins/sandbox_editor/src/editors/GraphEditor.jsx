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
        // --- [修复 1/7] 在加载数据时，为每个节点添加一个稳定的内部ID ---
        const nodesWithInternalIds = (graphData.nodes || []).map((node, index) => ({
            ...node,
            _internal_id: node.id + `_${Date.now()}_${index}`
        }));
        setNodes(nodesWithInternalIds);
    }, [graphData]);

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    const syncNodes = async (nodesToSave, optimisticState) => {
        setErrorMessage('');
        // 乐观更新UI，使用包含 _internal_id 的状态
        setNodes(optimisticState);
        try {
            await mutate(sandboxId, [{
                type: 'UPSERT',
                path: `${basePath}/nodes`,
                value: nodesToSave, // 只保存干净的数据到后端
            }]);
            // 确认最终状态
            setNodes(optimisticState);
        } catch (e) {
            setErrorMessage(`Failed to save graph changes: ${e.message}`);
            // 如果失败，回滚到操作前的状态 (此处的 'nodes' 是闭包捕获的旧状态)
            setNodes(nodes);
        }
    };
    
    const handleNodeDragEnd = async (event) => {
        const { active, over } = event;
        if (active.id !== over.id) {
            // --- [修复 2/7] 使用 _internal_id 来查找索引 ---
            const oldIndex = nodes.findIndex(n => n._internal_id === active.id);
            const newIndex = nodes.findIndex(n => n._internal_id === over.id);
            if (oldIndex === -1 || newIndex === -1) return;

            const reorderedNodes = arrayMove(nodes, oldIndex, newIndex);
            const nodesToSave = reorderedNodes.map(({_internal_id, ...rest}) => rest);
            await syncNodes(nodesToSave, reorderedNodes);
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
        const nodesToSave = nodes.map(({_internal_id, ...rest}) => rest);
        await syncNodes(nodesToSave, nodes);
        alert('Graph saved!');
    };
    
    const handleDeleteNode = async (internalIdToDelete) => {
        if (!window.confirm(`Are you sure you want to delete this node?`)) return;
        // --- [修复 3/7] 使用 _internal_id 进行过滤 ---
        const updatedNodes = nodes.filter(n => n._internal_id !== internalIdToDelete);
        const nodesToSave = updatedNodes.map(({_internal_id, ...rest}) => rest);
        await syncNodes(nodesToSave, updatedNodes);
    };

    const handleAddNode = () => {
        // --- [修复 4/7] 添加节点时，同时创建 _internal_id ---
        const newInternalId = `new_node_internal_${Date.now()}`;
        const newNode = { 
            _internal_id: newInternalId,
            id: `new_node_${Date.now()}`, 
            depends_on: [], 
            run: [], 
            metadata: {} 
        };
        setNodes(prev => [...prev, newNode]);
        // 使用 _internal_id 作为 key 来展开
        setExpandedNodes(prev => ({...prev, [newInternalId]: true}));
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

    // --- [修复 5/7] 使用 _internal_id 来切换展开状态 ---
    const toggleNodeExpand = (internalId) => {
        setExpandedNodes(prev => ({ ...prev, [internalId]: !prev[internalId] }));
    };

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
                    {/* --- [修复 6/7] 使用 _internal_id 作为 dnd-kit 的 ID 来源 --- */}
                    <SortableContext items={nodes.map(n => n._internal_id)} strategy={verticalListSortingStrategy}>
                        <List>
                            {nodes.map((node, index) => (
                                // --- [修复 7/7] 使用 _internal_id 作为 React key 和组件的唯一标识 ---
                                <div key={node._internal_id} ref={index === nodes.length -1 ? newNodeFormRef : null}>
                                    <SortableNodeItem
                                        id={node._internal_id}
                                        node={node}
                                        expanded={!!expandedNodes[node._internal_id]}
                                        onToggleExpand={() => toggleNodeExpand(node._internal_id)}
                                        onDelete={() => handleDeleteNode(node._internal_id)}
                                    >
                                        <Collapse in={!!expandedNodes[node._internal_id]} timeout="auto" unmountOnExit>
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