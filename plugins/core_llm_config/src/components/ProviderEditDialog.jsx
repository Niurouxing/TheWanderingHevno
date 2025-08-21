// plugins/core_llm_config/src/components/ProviderEditDialog.jsx

import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField,
    Box, IconButton, Typography, Tooltip
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';

export function ProviderEditDialog({ open, onClose, onSave, existingProviderIds }) {
    const [id, setId] = useState('');
    const [baseUrl, setBaseUrl] = useState('');
    const [mappings, setMappings] = useState([{ alias: '', canonical: '' }]);
    const [idError, setIdError] = useState('');

    useEffect(() => {
        if (!open) {
            // 关闭时重置状态
            setId('');
            setBaseUrl('');
            setMappings([{ alias: '', canonical: '' }]);
            setIdError('');
        }
    }, [open]);

    const handleIdChange = (e) => {
        const newId = e.target.value;
        setId(newId);
        if (!/^[a-zA-Z0-9_]+$/.test(newId) && newId) {
            setIdError('ID 只能包含字母、数字和下划线。');
        } else if (existingProviderIds.includes(newId)) {
            setIdError('该 ID 已存在。');
        } else {
            setIdError('');
        }
    };

    const handleMappingChange = (index, field, value) => {
        const newMappings = [...mappings];
        newMappings[index][field] = value;
        setMappings(newMappings);
    };

    const addMappingRow = () => {
        setMappings([...mappings, { alias: '', canonical: '' }]);
    };

    const removeMappingRow = (index) => {
        setMappings(mappings.filter((_, i) => i !== index));
    };

    const handleSave = () => {
        const finalMappings = mappings.reduce((acc, map) => {
            if (map.alias && map.canonical) {
                acc[map.alias] = map.canonical;
            }
            return acc;
        }, {});
        
        onSave({
            id: id,
            type: 'openai_compatible',
            base_url: baseUrl,
            model_mapping: finalMappings,
        });
    };

    const isSaveDisabled = !id || !baseUrl || !!idError;

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>添加 OpenAI 兼容提供商</DialogTitle>
            <DialogContent>
                <TextField
                    autoFocus
                    margin="dense"
                    label="提供商 ID"
                    fullWidth
                    variant="outlined"
                    value={id}
                    onChange={handleIdChange}
                    error={!!idError}
                    helperText={idError || "一个唯一的标识符，例如 'my_groq_proxy'。"}
                    required
                />
                <TextField
                    margin="dense"
                    label="API Base URL"
                    fullWidth
                    variant="outlined"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    helperText="API 的入口地址，例如 'https://api.groq.com/openai/v1'。"
                    required
                />
                <Box sx={{ mt: 3 }}>
                    <Typography gutterBottom>模型别名 (可选)</Typography>
                    {mappings.map((map, index) => (
                        <Box key={index} sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1 }}>
                            <TextField label="别名 (在图中使用)" size="small" value={map.alias} onChange={(e) => handleMappingChange(index, 'alias', e.target.value)} />
                            <TextField label="映射到 (规范模型)" size="small" value={map.canonical} onChange={(e) => handleMappingChange(index, 'canonical', e.target.value)} />
                            <Tooltip title="移除此行">
                                <span>
                                    <IconButton onClick={() => removeMappingRow(index)} disabled={mappings.length === 1}>
                                        <DeleteIcon />
                                    </IconButton>
                                </span>
                            </Tooltip>
                        </Box>
                    ))}
                    <Button startIcon={<AddCircleOutlineIcon />} onClick={addMappingRow} size="small">
                        添加一行
                    </Button>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>取消</Button>
                <Button onClick={handleSave} variant="contained" disabled={isSaveDisabled}>保存</Button>
            </DialogActions>
        </Dialog>
    );
}
