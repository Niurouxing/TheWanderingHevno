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

        // 1. 优先处理已经是数组的情况 (最常见)
        if (Array.isArray(value)) {
            isValid = true;
            parsedData = value;
        } 
        // 2. 处理空值 (null, undefined, '')
        else if (!value) {
            isValid = true;
            parsedData = [];
        } 
        // 3. 最后尝试处理字符串
        else if (typeof value === 'string') {
            try {
                const parsed = JSON.parse(value);
                if (Array.isArray(parsed)) {
                    isValid = true;
                    parsedData = parsed;
                }
            } catch (e) {
                // 解析失败，isValid 保持 false
            }
        }
        
        if (isValid) {
            // 清理数据，确保数组中的每一项都是具有所需键的有效对象
            const sanitized = parsedData.map(item => 
                (typeof item === 'object' && item !== null && !Array.isArray(item))
                    ? { codex: item.codex || '', source: item.source || '' }
                    : { codex: '', source: '' } // 如果项格式不正确，则重置
            );
            setSources(sanitized);
            setIsInvalidFormat(false);
        } else {
            setSources([]);
            setIsInvalidFormat(true);
        }
    }, [value]);

    const notifyChange = (newSources) => {
        // [核心修复] 直接传递原生数组，而不是JSON字符串
        onChange(newSources);
    };

    const handleItemChange = (index, field, fieldValue) => {
        const newSources = [...sources];
        newSources[index] = { ...newSources[index], [field]: fieldValue };
        setSources(newSources);
        notifyChange(newSources);
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
                            label="激活源 (宏)"
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