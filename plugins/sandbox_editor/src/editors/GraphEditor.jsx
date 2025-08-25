// plugins/sandbox_editor/src/editors/GraphEditor.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Box, Typography, List, Collapse, IconButton, Button, TextField, Alert, Chip, InputAdornment } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableNodeItem } from '../components/SortableNodeItem';
import { RuntimeEditor } from './RuntimeEditor';
import { mutate } from '../utils/api';
import { exportAsJson, importFromJson } from '../utils/fileUtils';
import { debounce } from '../utils/debounce';

export function GraphEditor({ sandboxId, basePath, graphName, graphData, onBack, confirmationService }) {
    const [nodes, setNodes] = useState([]);
    const [expandedNodes, setExpandedNodes] = useState({});
    const [errorMessage, setErrorMessage] = useState('');
    const newNodeFormRef = useRef(null);

    useEffect(() => {
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
        setNodes(optimisticState);
        try {
            await mutate(sandboxId, [{
                type: 'UPSERT',
                path: `${basePath}/nodes`,
                value: nodesToSave,
            }]);
            setNodes(optimisticState);
        } catch (e) {
            setErrorMessage(`Failed to save graph changes: ${e.message}`);
            throw e;
        }
    };
    
    const handleNodeDragEnd = async (event) => {
        const { active, over } = event;
        if (active.id !== over.id) {
            const oldIndex = nodes.findIndex(n => n._internal_id === active.id);
            const newIndex = nodes.findIndex(n => n._internal_id === over.id);
            if (oldIndex === -1 || newIndex === -1) return;

            const originalNodes = [...nodes];
            const reorderedNodes = arrayMove(nodes, oldIndex, newIndex);
            const nodesToSave = reorderedNodes.map(({_internal_id, ...rest}) => rest);
            await syncNodes(nodesToSave, reorderedNodes).catch(() => setNodes(originalNodes));
        }
    };
    
    const handleDeleteNode = async (internalIdToDelete) => {
        const confirmed = await confirmationService.confirm({
            title: '删除节点确认',
            message: '你确定要删除这个节点吗？',
        });
        if (!confirmed) return;
        
        const originalNodes = [...nodes];
        const updatedNodes = nodes.filter(n => n._internal_id !== internalIdToDelete);
        const nodesToSave = updatedNodes.map(({_internal_id, ...rest}) => rest);
        await syncNodes(nodesToSave, updatedNodes).catch(() => setNodes(originalNodes));
    };

    const handleAddNode = async () => {
        const newInternalId = `new_node_internal_${Date.now()}`;
        const newNode = { 
            _internal_id: newInternalId,
            id: `new_node_${Date.now()}`, 
            depends_on: [], 
            run: [], 
            metadata: {} 
        };
        const originalNodes = [...nodes];
        const updatedNodes = [...nodes, newNode];

        const nodesToSave = updatedNodes.map(({_internal_id, ...rest}) => rest);
        await syncNodes(nodesToSave, updatedNodes).catch(() => setNodes(originalNodes));
        
        setExpandedNodes(prev => ({...prev, [newInternalId]: true}));
        setTimeout(() => {
             newNodeFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 100);
    };

    const handleExportNode = (internalIdToExport) => {
        const nodeToExport = nodes.find(n => n._internal_id === internalIdToExport);
        if (!nodeToExport) {
            setErrorMessage('无法找到要导出的节点。');
            return;
        }
        const { _internal_id, ...cleanNode } = nodeToExport;
        exportAsJson(cleanNode, `${cleanNode.id}.json`);
    };

    const handleImportNode = async () => {
        try {
            const { data: importedNode } = await importFromJson();
            if (typeof importedNode !== 'object' || Array.isArray(importedNode) || importedNode === null) throw new Error("导入的文件必须是一个有效的JSON对象。");
            if (!importedNode.id) throw new Error("导入的节点缺少必需的 'id' 字段。");
            if (nodes.some(n => n.id === importedNode.id)) throw new Error(`ID为 "${importedNode.id}" 的节点已存在。`);

            const newNode = { ...importedNode, _internal_id: `${importedNode.id}_${Date.now()}_imported` };
            const originalNodes = [...nodes];
            const updatedNodes = [...nodes, newNode];
            const nodesToSave = updatedNodes.map(({_internal_id, ...rest}) => rest);
            await syncNodes(nodesToSave, updatedNodes).catch(() => setNodes(originalNodes));
            alert(`成功导入节点 "${newNode.id}"。更改已自动保存。`);
        } catch (e) {
            setErrorMessage(`导入节点失败: ${e.message}`);
        }
    };
    
    const debouncedSync = useCallback(debounce(async (nodesToSave, optimisticState) => {
        const originalNodes = [...nodes];
        try {
            await syncNodes(nodesToSave, optimisticState);
        } catch (e) {
            setNodes(originalNodes);
        }
    }, 500), [sandboxId, basePath]);

    const handleNodeChange = (index, field, value) => {
        const updatedNodes = [...nodes];
        let finalValue = value;
        if (field === 'depends_on' && typeof value === 'string') {
            finalValue = value.split(',').map(id => id.trim()).filter(Boolean)
        }
        updatedNodes[index] = { ...updatedNodes[index], [field]: finalValue };
        setNodes(updatedNodes);

        const nodesToSave = updatedNodes.map(({_internal_id, ...rest}) => rest);
        
        if (field === 'id' || field === 'depends_on') {
            debouncedSync(nodesToSave, updatedNodes);
        } else {
            syncNodes(nodesToSave, updatedNodes).catch(() => setNodes(nodes));
        }
    };

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
                <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={handleImportNode}>导入节点</Button>
                <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddNode}>添加节点</Button>
            </Box>
            {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage('')}>{errorMessage}</Alert>}

            <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleNodeDragEnd}>
                    <SortableContext items={nodes.map(n => n._internal_id)} strategy={verticalListSortingStrategy}>
                        <List>
                            {nodes.map((node, index) => (
                                <div key={node._internal_id} ref={index === nodes.length -1 ? newNodeFormRef : null}>
                                    <SortableNodeItem
                                        id={node._internal_id}
                                        node={node}
                                        expanded={!!expandedNodes[node._internal_id]}
                                        onToggleExpand={() => toggleNodeExpand(node._internal_id)}
                                        onDelete={() => handleDeleteNode(node._internal_id)}
                                        onExport={() => handleExportNode(node._internal_id)}
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