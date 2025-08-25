import React, { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogTitle, DialogContent, TextField, FormControlLabel, Switch, Typography, Alert, Box, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { debounce } from '../utils/debounce'; // 导入防抖工具

export function GenericEditorDialog({ open, onClose, onSave, item }) {
    if (!item) return null;

    const { path, value: initialValue } = item;
    
    const [dataType, setDataType] = useState('string');
    const [currentValue, setCurrentValue] = useState('');
    const [error, setError] = useState('');
    // --- [新增] 用于UI反馈的保存状态 ---
    const [saveState, setSaveState] = useState('idle'); // 'idle', 'saving', 'saved'

    // 使用 useCallback 和 debounce 来创建一个稳定的、防抖的保存函数
    const debouncedSave = useCallback(debounce(async (newValue) => {
        setError('');
        // --- [修改] 更新保存状态 ---
        setSaveState('saving');
        let finalValue;
        try {
            switch (dataType) {
                case 'boolean':
                    finalValue = newValue;
                    break;
                case 'number':
                    finalValue = Number(newValue);
                    if (isNaN(finalValue)) {
                        throw new Error("无效的数字格式。");
                    }
                    break;
                case 'json':
                    finalValue = JSON.parse(newValue);
                    break;
                case 'string':
                default:
                    finalValue = newValue;
                    break;
            }
            await onSave(path, finalValue);
            // --- [修改] 更新保存状态 ---
            setSaveState('saved');
        } catch (e) {
            setError(`自动保存失败: ${e.message}`);
            // --- [修改] 更新保存状态 ---
            setSaveState('idle'); 
        }
    }, 500), [dataType, path, onSave]);

    useEffect(() => {
        if (open && item) {
            setError('');
            setSaveState('idle'); // 每次打开或切换item时重置状态
            const type = typeof initialValue;
            let val;
            if (type === 'boolean') {
                setDataType('boolean');
                val = initialValue;
            } else if (type === 'string') {
                setDataType('string');
                val = initialValue;
            } else if (type === 'number') {
                setDataType('number');
                val = String(initialValue);
            } else if (type === 'object' && initialValue !== null) {
                setDataType('json');
                val = JSON.stringify(initialValue, null, 2);
            } else {
                setDataType('json');
                val = 'null';
            }
            setCurrentValue(val);
        }
    }, [open, item, initialValue]);

    const handleValueChange = (newValue) => {
        setCurrentValue(newValue);
        // --- [修改] 当用户开始输入时，重置保存状态 ---
        setSaveState('idle');
        debouncedSave(newValue);
    };

    const renderInput = () => {
        switch (dataType) {
            case 'boolean':
                return <FormControlLabel control={<Switch checked={!!currentValue} onChange={(e) => handleValueChange(e.target.checked)} />} label={currentValue ? 'True / On' : 'False / Off'} />;
            case 'string':
                return <TextField label="值" value={currentValue} onChange={(e) => handleValueChange(e.target.value)} fullWidth multiline minRows={3} variant="outlined" autoFocus />;
            case 'number':
                return <TextField label="值" type="number" value={currentValue} onChange={(e) => handleValueChange(e.target.value)} fullWidth variant="outlined" autoFocus />;
            case 'json':
                return <TextField label="值 (JSON格式)" value={currentValue} onChange={(e) => handleValueChange(e.target.value)} fullWidth multiline minRows={10} variant="outlined" autoFocus sx={{ fontFamily: 'monospace' }} />;
            default:
                return <Typography color="error">不支持的数据类型。</Typography>;
        }
    };
    
    const getSaveStateMessage = () => {
        switch (saveState) {
            case 'saving': return '正在保存...';
            case 'saved': return '已保存';
            default: return '';
        }
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
            <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                编辑值
                <IconButton onClick={onClose}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent>
                <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                        <Typography variant="caption" display="block" color="text.secondary">
                            路径: {path}
                        </Typography>
                        <Typography variant="caption" display="block" color="text.secondary">
                            类型: {dataType}
                        </Typography>
                    </Box>
                    {/* --- [新增] 保存状态指示器 --- */}
                    <Typography variant="caption" color="text.secondary">
                        {getSaveStateMessage()}
                    </Typography>
                </Box>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                {renderInput()}
            </DialogContent>
        </Dialog>
    );
}