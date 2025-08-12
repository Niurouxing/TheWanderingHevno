// plugins/core_llm_config/src/components/KeyStatusTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip,
    Typography, IconButton, Tooltip
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { Countdown } from './Countdown'; // 我们将倒计时逻辑移到自己的组件中

export function KeyStatusTable({ keys, onDelete, isDeleting }) {
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

    return (
        <TableContainer component={Paper} variant="outlined">
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>密钥 (后4位)</TableCell>
                        <TableCell>状态</TableCell>
                        <TableCell>可用时间</TableCell>
                        <TableCell align="right">操作</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {keys.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={4} align="center">
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
    );
}