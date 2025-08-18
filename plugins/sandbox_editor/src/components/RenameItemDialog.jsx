import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Alert } from '@mui/material';

export function RenameItemDialog({ open, onClose, onRename, item, existingKeys = [] }) {
    if (!item) return null;

    const { path } = item;
    const oldKey = path.split('/').pop();

    const [newKey, setNewKey] = useState(oldKey);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (open) {
            setNewKey(oldKey);
            setError('');
            setLoading(false);
        }
    }, [open, oldKey]);

    const handleRename = async () => {
        setError('');
        const trimmedKey = newKey.trim();

        if (!trimmedKey) {
            setError('名称不能为空。');
            return;
        }
        if (trimmedKey === oldKey) {
            onClose(); // 名称未改变，直接关闭
            return;
        }
        if (existingKeys.includes(trimmedKey)) {
            setError(`名称 "${trimmedKey}" 已存在，请使用其他名称。`);
            return;
        }

        setLoading(true);
        try {
            await onRename(path, trimmedKey);
            // 成功后，父组件会处理关闭
        } catch (e) {
            setError(`重命名失败: ${e.message}`);
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>重命名 "{oldKey}"</DialogTitle>
            <DialogContent>
                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
                <TextField
                    label="新名称"
                    value={newKey}
                    onChange={e => setNewKey(e.target.value)}
                    fullWidth
                    required
                    autoFocus
                    margin="dense"
                    onKeyPress={(e) => e.key === 'Enter' && handleRename()}
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={loading}>取消</Button>
                <Button onClick={handleRename} variant="contained" disabled={loading}>
                    {loading ? '正在保存...' : '保存'}
                </Button>
            </DialogActions>
        </Dialog>
    );
}
