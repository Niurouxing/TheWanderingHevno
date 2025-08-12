// plugins/sandbox_editor/src/editors/LlmContentsEditor.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { Box, List, Collapse, IconButton, Button, Menu, MenuItem, Typography, Paper, TextField, Select, InputLabel, FormControl, Chip } from '@mui/material';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import MessageIcon from '@mui/icons-material/Message';
import DynamicFeedIcon from '@mui/icons-material/DynamicFeed';

// Inner component for rendering the sortable list item and its form
function SortableContentItem({ id, item, onUpdate, onDelete, allItems }) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
    const [isExpanded, setIsExpanded] = useState(false);

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 1 : 0,
        position: 'relative',
        marginBottom: '8px',
    };
    
    const handleFieldChange = (field, value) => {
        onUpdate({ ...item, [field]: value });
    };

    const renderHeader = () => {
        if (item.type === 'MESSAGE_PART') {
            return <>
                <MessageIcon sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography sx={{ flexGrow: 1 }}>消息片段</Typography>
                <Chip label={item.role || 'no role'} size="small" variant="outlined" />
            </>;
        }
        if (item.type === 'INJECT_MESSAGES') {
            return <>
                <DynamicFeedIcon sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography sx={{ flexGrow: 1 }}>注入消息</Typography>
            </>;
        }
        return 'Unknown Item';
    };

    return (
        <Paper ref={setNodeRef} style={style} variant="outlined">
            <Box sx={{ display: 'flex', alignItems: 'center', p: 1, backgroundColor: 'rgba(255,255,255,0.05)', cursor: 'pointer' }} onClick={() => setIsExpanded(!isExpanded)}>
                <Box {...attributes} {...listeners} sx={{ cursor: 'grab', display: 'flex', alignItems: 'center', mr:1 }}>
                    <DragIndicatorIcon />
                </Box>
                {renderHeader()}
                <IconButton size="small" sx={{ ml: 1 }}><ChevronRightIcon sx={{ transform: isExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} /></IconButton>
                <IconButton size="small" sx={{ ml: 1 }} onClick={(e) => { e.stopPropagation(); onDelete(); }}><DeleteIcon /></IconButton>
            </Box>
            <Collapse in={isExpanded}>
                <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {item.type === 'MESSAGE_PART' && <>
                        <FormControl fullWidth size="small">
                            <InputLabel>角色</InputLabel>
                            <Select label="角色" value={item.role || 'user'} onChange={(e) => handleFieldChange('role', e.target.value)}>
                                <MenuItem value="system">system</MenuItem>
                                <MenuItem value="user">user</MenuItem>
                                <MenuItem value="model">model</MenuItem>
                            </Select>
                        </FormControl>
                        <TextField label="内容 (支持宏)" multiline minRows={3} value={item.content || ''} onChange={(e) => handleFieldChange('content', e.target.value)} />
                        <TextField label="是否启用 (支持宏，留空为 true)" size="small" value={item.is_enabled || ''} onChange={(e) => handleFieldChange('is_enabled', e.target.value)} />
                    </>}
                     {item.type === 'INJECT_MESSAGES' && <>
                        <TextField label="来源 (必须是宏)" multiline minRows={2} value={item.source || ''} onChange={(e) => handleFieldChange('source', e.target.value)} />
                        <TextField label="是否启用 (支持宏，留空为 true)" size="small" value={item.is_enabled || ''} onChange={(e) => handleFieldChange('is_enabled', e.target.value)} />
                    </>}
                </Box>
            </Collapse>
        </Paper>
    );
}


// Main editor component
export function LlmContentsEditor({ contents, onContentsChange }) {
    const [items, setItems] = useState([]);
    const [anchorEl, setAnchorEl] = useState(null);

    // --- [修复] 修改 useEffect 逻辑以稳定 _internal_id ---
    useEffect(() => {
        setItems(prevItems => {
            // 创建一个映射，用于快速查找现有项的 _internal_id
            const idMap = new Map(prevItems.map(item => [JSON.stringify({type: item.type, role: item.role, content: item.content, source: item.source}), item._internal_id]));

            const newItems = (contents || []).map((item, index) => {
                // 如果是新添加的项（长度变化），或者在旧项中找不到，则生成新的 ID
                if (prevItems.length !== contents.length || !prevItems[index] || !prevItems[index]._internal_id) {
                     return {
                        ...item,
                        _internal_id: `${item.type}_${Date.now()}_${index}`
                    };
                }
                // 否则，保留旧的 ID
                return {
                    ...item,
                    _internal_id: prevItems[index]._internal_id
                };
            });
            return newItems;
        });
    }, [contents]); // 依赖仍然是 contents，但内部逻辑更智能了

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor)
    );
    
    const notifyParent = (newItems) => {
        // 在通知父组件之前，移除内部使用的 _internal_id
        const cleanedItems = newItems.map(({ _internal_id, ...rest }) => rest);
        onContentsChange(cleanedItems);
    }

    const handleDragEnd = (event) => {
        const { active, over } = event;
        if (active && over && active.id !== over.id) {
            const oldIndex = items.findIndex(item => item._internal_id === active.id);
            const newIndex = items.findIndex(item => item._internal_id === over.id);
            const newOrderedItems = arrayMove(items, oldIndex, newIndex);
            setItems(newOrderedItems);
            notifyParent(newOrderedItems);
        }
    };
    
    const handleAddItem = (type) => {
        let newItem;
        if (type === 'MESSAGE_PART') {
            newItem = { type: 'MESSAGE_PART', role: 'user', content: '' };
        } else {
            newItem = { type: 'INJECT_MESSAGES', source: '' };
        }
        // 在添加时就生成稳定的 _internal_id
        const updatedItems = [...items, { ...newItem, _internal_id: `${type}_${Date.now()}_${items.length}` }];
        setItems(updatedItems);
        notifyParent(updatedItems);
        handleCloseMenu();
    };

    const handleUpdateItem = (index, updatedItem) => {
        const newItems = [...items];
        // 确保更新时 _internal_id 不会丢失
        newItems[index] = { ...updatedItem, _internal_id: items[index]._internal_id };
        setItems(newItems);
        notifyParent(newItems);
    };

    const handleDeleteItem = (index) => {
        const newItems = items.filter((_, i) => i !== index);
        setItems(newItems);
        notifyParent(newItems);
    };

    const handleOpenMenu = (event) => setAnchorEl(event.currentTarget);
    const handleCloseMenu = () => setAnchorEl(null);

    return (
        <Paper variant="outlined" sx={{ p: 1, borderColor: 'rgba(255, 255, 255, 0.23)' }}>
            <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1 }}>
                对话内容 (Contents)
            </Typography>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={items.map(i => i._internal_id)} strategy={verticalListSortingStrategy}>
                    <List disablePadding>
                        {items.map((item, index) => (
                            <SortableContentItem
                                key={item._internal_id}
                                id={item._internal_id}
                                item={item}
                                onUpdate={(updated) => handleUpdateItem(index, updated)}
                                onDelete={() => handleDeleteItem(index)}
                            />
                        ))}
                    </List>
                </SortableContext>
            </DndContext>
            {items.length === 0 && (
                 <Typography variant="body2" color="text.secondary" align="center" sx={{p: 2}}>
                    No content defined. Click "Add Item" to start.
                </Typography>
            )}
            <Box sx={{ mt: 1 }}>
                <Button startIcon={<AddIcon />} onClick={handleOpenMenu} size="small" variant="outlined">
                    添加条目
                </Button>
                <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleCloseMenu}>
                    <MenuItem onClick={() => handleAddItem('MESSAGE_PART')}><MessageIcon sx={{ mr: 1 }} />消息片段</MenuItem>
                    <MenuItem onClick={() => handleAddItem('INJECT_MESSAGES')}><DynamicFeedIcon sx={{ mr: 1 }} />注入消息</MenuItem>
                </Menu>
            </Box>
        </Paper>
    );
}