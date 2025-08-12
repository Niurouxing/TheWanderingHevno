// plugins/core_runner_ui/src/components/SnapshotHistory.jsx
import React from 'react';
import { List, ListItem, ListItemButton, ListItemText, ListItemIcon, Tooltip, Box, Typography,IconButton } from '@mui/material';
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import HistoryToggleOffIcon from '@mui/icons-material/HistoryToggleOff';

// 辅助函数，从快照中提取简短摘要
const getSnapshotSummary = (snapshot) => {
    const input = snapshot.triggering_input?.text;
    if (input) {
        return `输入: "${input.slice(0, 30)}${input.length > 30 ? '...' : ''}"`;
    }
    
    // 尝试寻找与上一个快照相比的新消息
    if (snapshot.moment?.memoria?.chat_history) {
        const entries = snapshot.moment.memoria.chat_history.entries;
        if (entries && entries.length > 0) {
            const lastEntry = entries[entries.length - 1];
            if (lastEntry.level === 'model') {
                return `回应: "${lastEntry.content.slice(0, 30)}${lastEntry.content.length > 30 ? '...' : ''}"`;
            }
        }
    }
    return '初始状态';
};

export const SnapshotHistory = ({ history, headSnapshotId, onRevert, isLoading }) => {
    if (!history || history.length === 0) {
        return (
            <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
                <Typography>没有历史记录</Typography>
            </Box>
        );
    }
    
    // 按时间倒序显示
    const reversedHistory = [...history].reverse();

    return (
        <List dense disablePadding>
            {reversedHistory.map(snapshot => {
                const isHead = snapshot.id === headSnapshotId;
                const summary = getSnapshotSummary(snapshot);
                const timestamp = new Date(snapshot.created_at).toLocaleString();

                return (
                    <ListItem
                        key={snapshot.id}
                        disablePadding
                        secondaryAction={
                            !isHead && (
                                <Tooltip title="切换到此状态">
                                    <IconButton edge="end" onClick={() => onRevert(snapshot.id)} disabled={isLoading}>
                                        <HistoryToggleOffIcon />
                                    </IconButton>
                                </Tooltip>
                            )
                        }
                    >
                        <ListItemButton selected={isHead} dense>
                            <ListItemIcon sx={{ minWidth: 32 }}>
                                {isHead ? <RadioButtonCheckedIcon color="primary" fontSize="small" /> : <RadioButtonUncheckedIcon fontSize="small" />}
                            </ListItemIcon>
                            <ListItemText
                                primary={summary}
                                secondary={timestamp}
                                primaryTypographyProps={{ noWrap: true, variant: 'body2' }}
                                secondaryTypographyProps={{ noWrap: true, variant: 'caption' }}
                            />
                        </ListItemButton>
                    </ListItem>
                );
            })}
        </List>
    );
};