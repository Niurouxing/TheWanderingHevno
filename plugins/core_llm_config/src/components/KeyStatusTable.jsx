// plugins/core_llm_config/src/components/KeyStatusTable.jsx
import React, { useState } from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip,
    Typography, IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions,
    Button, TextField, Box
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { Countdown } from './Countdown'; // 我们将倒计时逻辑移到自己的组件中

export function KeyStatusTable({ keys, onDelete, onUpdateConcurrency, isDeleting }) {
    const [editingKey, setEditingKey] = useState(null);
    const [newConcurrency, setNewConcurrency] = useState(1);

    const getStatusChip = (key) => {
        switch (key.status) {
            case 'available':
                return <Chip label="可用" color="success" size="small" />;
            case 'rate_limited':
                return <Chip label="限速中" color="warning" size="small" />;
            case 'banned':
                return <Chip label="已禁用" color="error" size="small" />;
            default:
                return <Chip label={key.status} size="small" />;
        }
    };

    const handleEditConcurrency = (key) => {
        setEditingKey(key);
        setNewConcurrency(key.max_concurrency || 1);
    };

    const handleSaveConcurrency = async () => {
        if (editingKey && onUpdateConcurrency) {
            await onUpdateConcurrency(editingKey.key_suffix, newConcurrency);
            setEditingKey(null);
        }
    };

    const handleCancelEdit = () => {
        setEditingKey(null);
        setNewConcurrency(1);
    };

    return (
        <>
        <TableContainer component={Paper} variant="outlined">
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>密钥 (后4位)</TableCell>
                        <TableCell>状态</TableCell>
                        <TableCell>最大并发数</TableCell>
                        <TableCell>可用时间</TableCell>
                        <TableCell align="right">操作</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {keys.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={5} align="center">
                                <Typography color="text.secondary" sx={{ p: 2 }}>
                                    未找到为该提供商配置的密钥。
                                </Typography>
                            </TableCell>
                        </TableRow>
                    )}
                    {keys.map((key) => (
                        <TableRow key={key.key_suffix}>
                            <TableCell component="th" scope="row">
                                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                    {key.key_suffix}
                                </Typography>
                            </TableCell>
                            <TableCell>{getStatusChip(key)}</TableCell>
                            <TableCell>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Chip 
                                        label={key.max_concurrency || 1} 
                                        size="small" 
                                        variant="outlined"
                                        color="primary"
                                    />
                                    <Tooltip title="编辑并发数">
                                        <IconButton
                                            size="small"
                                            onClick={() => handleEditConcurrency(key)}
                                            disabled={isDeleting}
                                        >
                                            <EditIcon fontSize="small" />
                                        </IconButton>
                                    </Tooltip>
                                </Box>
                            </TableCell>
                            <TableCell>
                                {key.status === 'rate_limited' && key.rate_limit_until ?
                                    <Countdown until={key.rate_limit_until} />
                                    : '—'}
                            </TableCell>
                            <TableCell align="right">
                                <Tooltip title="从 .env 文件中删除此密钥">
                                    <span>
                                        <IconButton
                                            size="small"
                                            color="error"
                                            onClick={() => onDelete(key.key_suffix)}
                                            disabled={isDeleting}
                                        >
                                            <DeleteIcon fontSize="small" />
                                        </IconButton>
                                    </span>
                                </Tooltip>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
        
        {/* 编辑并发数对话框 */}
        <Dialog open={!!editingKey} onClose={handleCancelEdit} maxWidth="sm" fullWidth>
            <DialogTitle>编辑密钥并发数</DialogTitle>
            <DialogContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    密钥: {editingKey?.key_suffix}
                </Typography>
                <TextField
                    autoFocus
                    type="number"
                    label="最大并发数"
                    value={newConcurrency}
                    onChange={(e) => setNewConcurrency(Math.max(1, parseInt(e.target.value) || 1))}
                    inputProps={{ min: 1, max: 100 }}
                    variant="outlined"
                    size="small"
                    fullWidth
                    helperText="范围: 1-100。并发数决定了该密钥可以同时处理的请求数量。"
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={handleCancelEdit}>取消</Button>
                <Button 
                    onClick={handleSaveConcurrency} 
                    variant="contained"
                    disabled={isDeleting}
                >
                    保存
                </Button>
            </DialogActions>
        </Dialog>
        </>
    );
}