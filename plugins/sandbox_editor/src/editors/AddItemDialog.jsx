import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Select, MenuItem, FormControl, InputLabel, Box, Switch, FormControlLabel, Alert, Divider } from '@mui/material';
import { importFromJson } from '../utils/fileUtils';
import UploadFileIcon from '@mui/icons-material/UploadFile';

// 预定义的 hevno 类型模板，方便用户快速创建
const PREFAB_TEMPLATES = {
    'hevno/graph': {
        __hevno_type__: 'hevno/graph',
        nodes: [],
        metadata: {},
    },
    'hevno/codex': {
        __hevno_type__: 'hevno/codex',
        entries: [],
        description: 'A new codex.',
    },
    'hevno/memoria': {
        __hevno_type__: 'hevno/memoria',
        __global_sequence__: 0,
    }
};

export function AddItemDialog({ open, onClose, onAdd, parentPath, existingKeys = [] }) {
    const [key, setKey] = useState('');
    const [type, setType] = useState('string');
    const [value, setValue] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        if (open) {
            // 重置状态
            setKey('');
            setType('string');
            setValue('');
            setError('');
        }
    }, [open]);

    const handleAdd = async () => {
        setError('');
        if (!key.trim()) {
            setError('Key is required.');
            return;
        }
        if (existingKeys.includes(key.trim())) {
            setError(`Key "${key.trim()}" already exists at this level.`);
            return;
        }

        let finalValue;
        try {
            switch (type) {
                case 'string': finalValue = value; break;
                case 'number':
                    finalValue = Number(value);
                    if (isNaN(finalValue)) throw new Error("Invalid number.");
                    break;
                case 'boolean': finalValue = value === 'true'; break;
                case 'object': finalValue = {}; break;
                case 'array': finalValue = []; break;
                case 'hevno/graph':
                case 'hevno/codex':
                case 'hevno/memoria':
                    finalValue = PREFAB_TEMPLATES[type]; break;
                default:
                    throw new Error("Invalid type selected.");
            }
            await onAdd(parentPath, key.trim(), finalValue);
        } catch (e) {
            setError(`Failed to add item: ${e.message}`);
        }
    };

    const handleImport = async () => {
        try {
            const { data, filename } = await importFromJson();
            const keyFromFile = filename.toLowerCase().endsWith('.json')
                ? filename.slice(0, -5)
                : filename;

            // 检查导入的 key 是否冲突
            if (existingKeys.includes(keyFromFile)) {
                setError(`键 "${keyFromFile}" (来自文件名) 已存在。请先手动重命名文件或在下方修改键名。`);
                setKey(keyFromFile); // 填充键名让用户修改
            } else {
                // 如果不冲突，直接添加
                await onAdd(parentPath, keyFromFile, data);
                onClose(); // 成功后关闭对话框
            }
        } catch (e) {
            setError(`导入失败: ${e.message}`);
        }
    };

    const renderValueInput = () => {
        switch (type) {
            case 'string':
                return <TextField label="Value" value={value} onChange={e => setValue(e.target.value)} fullWidth autoFocus margin="dense" />;
            case 'number':
                return <TextField label="Value" type="number" value={value} onChange={e => setValue(e.target.value)} fullWidth autoFocus margin="dense" />;
            case 'boolean':
                return <FormControlLabel control={<Switch checked={value === 'true'} onChange={(e) => setValue(String(e.target.checked))} />} label={value === 'true' ? 'True' : 'False'} sx={{mt:1}} />;
            case 'object':
            case 'array':
            case 'hevno/graph':
            case 'hevno/codex':
            case 'hevno/memoria':
                // 这些类型不需要用户输入初始值
                return null; 
            default:
                return null;
        }
    };

    if (!open) return null;

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>加入新对象到 "{parentPath}"</DialogTitle>
            <DialogContent>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Button
                        variant="outlined"
                        startIcon={<UploadFileIcon />}
                        onClick={handleImport}
                    >
                        从JSON文件导入并添加
                    </Button>
                    <Divider>或手动创建</Divider>
                </Box>

                <TextField label="键 / 名称" value={key} onChange={e => setKey(e.target.value)} fullWidth required autoFocus margin="dense" />
                <FormControl fullWidth margin="dense">
                    <InputLabel id="add-item-type-label">类型</InputLabel>
                    <Select labelId="add-item-type-label" value={type} label="类型" onChange={e => setType(e.target.value)}>
                        <MenuItem value="string">字符串</MenuItem>
                        <MenuItem value="number">数字</MenuItem>
                        <MenuItem value="boolean">布尔值</MenuItem>
                        <MenuItem value="object">对象（空）</MenuItem>
                        <MenuItem value="array">数组（空）</MenuItem>
                        <MenuItem value="hevno/graph">预制件：图</MenuItem>
                        <MenuItem value="hevno/codex">预制件：Codex</MenuItem>
                        <MenuItem value="hevno/memoria">预制件：Memoria</MenuItem>
                    </Select>   
                </FormControl>
                {renderValueInput()}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>取消</Button>
                <Button onClick={handleAdd} variant="contained">添加</Button>
            </DialogActions>
        </Dialog>
    );
}