// plugins/sandbox_editor/src/editors/CodexInvokeEditor.jsx
import React, { useState, useEffect } from 'react';
import { Paper, List, ListItem, TextField, IconButton, Button, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';

export function CodexInvokeEditor({ value, onChange }) {
    const [sources, setSources] = useState([]);
    const [isInvalidFormat, setIsInvalidFormat] = useState(false);

    useEffect(() => {
        let parsedData = null;
        let isValid = false;

        // 优雅地处理空值、null或undefined
        if (!value) {
            isValid = true;
            parsedData = [];
        } 
        // 处理数据已经是JavaScript数组的情况
        else if (Array.isArray(value)) {
            isValid = true;
            parsedData = value;
        }
        // 处理数据是JSON字符串的情况
        else if (typeof value === 'string') {
            // 避免解析空字符串导致错误
            if (value.trim() === '') {
                isValid = true;
                parsedData = [];
            } else {
                try {
                    const parsed = JSON.parse(value);
                    if (Array.isArray(parsed)) {
                        isValid = true;
                        parsedData = parsed;
                    }
                } catch (e) {
                    // 如果解析失败，isValid 保持 false
                }
            }
        }
        
        if (isValid) {
            // 清理数据，确保数组中的每一项都是有效对象
            const sanitized = parsedData.map(item => 
                (typeof item === 'object' && item !== null && !Array.isArray(item))
                    ? { codex: item.codex || '', source: item.source || '' }
                    : { codex: '', source: '' }
            );
            setSources(sanitized);
            setIsInvalidFormat(false);
        } else {
            setSources([]);
            setIsInvalidFormat(true);
        }
        // --- [FIX END] ---

    }, [value]);

    const notifyChange = (newSources) => {
        try {
            // 始终将字符串化的JSON数组向上传递，以保持数据一致性
            const newValueString = JSON.stringify(newSources);
            onChange(newValueString);
        } catch (e) {
            console.error("Failed to stringify sources:", e);
        }
    };

    const handleItemChange = (index, field, fieldValue) => {
        const newSources = [...sources];
        newSources[index] = { ...newSources[index], [field]: fieldValue };
        setSources(newSources); // 立即更新本地UI
        notifyChange(newSources); // 将更改向上传播
    };

    const handleAddItem = () => {
        const newSources = [...sources, { codex: '', source: '' }];
        setSources(newSources);
        notifyChange(newSources);
    };

    const handleDeleteItem = (index) => {
        const newSources = sources.filter((_, i) => i !== index);
        setSources(newSources);
        notifyChange(newSources);
    };

    if (isInvalidFormat) {
        return (
            <Typography color="error.main" variant="body2" sx={{mt: 1}}>
                'from' 字段中的数据格式无效。请修正或清空以使用此编辑器。
            </Typography>
        )
    }

    return (
        <Paper variant="outlined" sx={{ p: 1.5, mt: 1, borderColor: 'rgba(255, 255, 255, 0.23)' }}>
             <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1 }}>
                Codex 数据源
            </Typography>
            <List disablePadding>
                {sources.map((item, index) => (
                    <ListItem key={index} disablePadding sx={{ display: 'flex', gap: 1, mb: 1.5, alignItems: 'center' }}>
                        <TextField
                            label="Codex 名称"
                            value={item.codex || ''}
                            onChange={(e) => handleItemChange(index, 'codex', e.target.value)}
                            size="small"
                            fullWidth
                            variant="outlined"
                            placeholder='例如, "npc_status"'
                        />
                        <TextField
                            label="来源 (宏)"
                            value={item.source || ''}
                            onChange={(e) => handleItemChange(index, 'source', e.target.value)}
                            size="small"
                            fullWidth
                            variant="outlined"
                            placeholder='例如, "{{pipe.input.text}}"'
                        />
                        <IconButton onClick={() => handleDeleteItem(index)} color="error" title="删除数据源">
                            <DeleteIcon />
                        </IconButton>
                    </ListItem>
                ))}
                {sources.length === 0 && <Typography variant="body2" color="text.secondary" align="center" sx={{mb: 1}}>未定义数据源。</Typography>}
            </List>
            <Button startIcon={<AddIcon />} onClick={handleAddItem} size="small" variant="outlined">
                添加数据源
            </Button>
        </Paper>
    );
};