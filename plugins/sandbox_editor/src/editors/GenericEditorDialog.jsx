import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, FormControlLabel, Switch, Typography, Alert, Box } from '@mui/material';

export function GenericEditorDialog({ open, onClose, onSave, item }) {
    // 如果没有 item，则提前返回，防止渲染错误
    if (!item) return null;

    const { path, value: initialValue } = item;
    
    const [dataType, setDataType] = useState('string');
    const [currentValue, setCurrentValue] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        if (open && item) {
            setError('');
            const type = typeof initialValue;
            if (type === 'boolean') {
                setDataType('boolean');
                setCurrentValue(initialValue);
            } else if (type === 'string') {
                setDataType('string');
                setCurrentValue(initialValue);
            } else if (type === 'number') {
                setDataType('number');
                setCurrentValue(String(initialValue));
            } else if (type === 'object' && initialValue !== null) {
                setDataType('json');
                setCurrentValue(JSON.stringify(initialValue, null, 2));
            } else { // 处理 null
                setDataType('json');
                setCurrentValue('null');
            }
        }
    }, [open, item, initialValue]);

    const handleSave = async () => {
        setError('');
        let finalValue;
        try {
            switch (dataType) {
                case 'boolean':
                    finalValue = currentValue;
                    break;
                case 'number':
                    finalValue = Number(currentValue);
                    if (isNaN(finalValue)) {
                        throw new Error("无效的数字格式。");
                    }
                    break;
                case 'json':
                    finalValue = JSON.parse(currentValue);
                    break;
                case 'string':
                default:
                    finalValue = currentValue;
                    break;
            }
            // onSave 是一个 async 函数
            await onSave(path, finalValue);
        } catch (e) {
            setError(`保存失败: ${e.message}`);
        }
    };

    const renderInput = () => {
        switch (dataType) {
            case 'boolean':
                return <FormControlLabel control={<Switch checked={!!currentValue} onChange={(e) => setCurrentValue(e.target.checked)} />} label={currentValue ? 'True / On' : 'False / Off'} />;
            case 'string':
                return <TextField label="值" value={currentValue} onChange={(e) => setCurrentValue(e.target.value)} fullWidth multiline minRows={3} variant="outlined" autoFocus />;
            case 'number':
                return <TextField label="值" type="number" value={currentValue} onChange={(e) => setCurrentValue(e.target.value)} fullWidth variant="outlined" autoFocus />;
            case 'json':
                return <TextField label="值 (JSON格式)" value={currentValue} onChange={(e) => setCurrentValue(e.target.value)} fullWidth multiline minRows={10} variant="outlined" autoFocus sx={{ fontFamily: 'monospace' }} />;
            default:
                return <Typography color="error">不支持的数据类型。</Typography>;
        }
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
            <DialogTitle>编辑值</DialogTitle>
            <DialogContent>
                <Box sx={{ mb: 2 }}>
                    <Typography variant="caption" display="block" color="text.secondary">
                        路径: {path}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                        类型: {dataType}
                    </Typography>
                </Box>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                {renderInput()}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>取消</Button>
                <Button onClick={handleSave} variant="contained">保存</Button>
            </DialogActions>
        </Dialog>
    );
}