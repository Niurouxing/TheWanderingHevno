// plugins/core_llm_config/src/components/KeyStatusTable.jsx
import React from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip, Typography, Box, Tooltip
} from '@mui/material';

function Countdown({ until }) {
    const [timeLeft, setTimeLeft] = React.useState(Math.round(until - Date.now() / 1000));

    React.useEffect(() => {
        if (timeLeft <= 0) return;
        const timer = setInterval(() => {
            setTimeLeft(prev => prev - 1);
        }, 1000);
        return () => clearInterval(timer);
    }, [timeLeft]);

    return timeLeft > 0 ? `${timeLeft}s` : 'Available';
}

export function KeyStatusTable({ keys }) {
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
                    </TableRow>
                </TableHead>
                <TableBody>
                    {keys.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={3} align="center">
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
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}