// plugins/core_runner_ui/src/components/SnapshotHistoryDrawer.jsx
import React from 'react';
import { 
    Drawer, List, ListItem, ListItemButton, ListItemText, ListItemIcon, 
    Tooltip, Box, Typography, IconButton, Divider, Toolbar, Skeleton
} from '@mui/material';
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';

const getSnapshotSummary = (snapshot) => {
    const input = snapshot.triggering_input?.text;
    if (input) {
        return `输入: "${input.slice(0, 35)}${input.length > 35 ? '...' : ''}"`;
    }
    
    const entries = snapshot.moment?.memoria?.chat_history?.entries;
    if (entries && entries.length > 0) {
        const lastEntry = entries[entries.length - 1];
        if (lastEntry.level === 'model') {
            return `回应: "${lastEntry.content.slice(0, 35)}${lastEntry.content.length > 35 ? '...' : ''}"`;
        }
    }
    return '初始状态';
};

export const SnapshotHistoryDrawer = ({ history, headSnapshotId, onRevert, onDelete, isLoading, width, ...drawerProps }) => {
    
    const reversedHistory = [...history].reverse();

    const drawerContent = (
        <>
            <Toolbar>
                <Typography variant="h6" component="div">交互历史</Typography>
            </Toolbar>
            <Divider />
            {history.length === 0 && !isLoading && (
                <Box sx={{ p: 2, textAlign: 'center', color: 'text.secondary' }}>
                    <Typography>没有历史记录</Typography>
                </Box>
            )}
            {isLoading && history.length === 0 && (
                <Box sx={{p: 2}}>
                    <Skeleton variant="text" sx={{ fontSize: '1rem' }} />
                    <Skeleton variant="text" sx={{ fontSize: '1rem' }} />
                    <Skeleton variant="text" sx={{ fontSize: '1rem' }} />
                </Box>
            )}
            <List dense disablePadding sx={{ flexGrow: 1, overflowY: 'auto' }}>
                {reversedHistory.map(snapshot => {
                    const isHead = snapshot.id === headSnapshotId;
                    const summary = getSnapshotSummary(snapshot);
                    const timestamp = new Date(snapshot.created_at).toLocaleString();

                    return (
                        <ListItem
                            key={snapshot.id}
                            disablePadding
                            secondaryAction={
                                // 只在非当前 head 的快照上显示删除按钮
                                !isHead && (
                                    <Tooltip title="永久删除此记录点">
                                        <span>
                                            <IconButton edge="end" onClick={() => onDelete(snapshot.id)} disabled={isLoading} sx={{ color: 'error.light' }}>
                                                <DeleteForeverIcon />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                )
                            }
                        >
                            <ListItemButton 
                                selected={isHead} 
                                dense
                                // 只有非当前 head 的快照才能被点击
                                onClick={!isHead ? () => onRevert(snapshot.id) : undefined} 
                                // 如果正在加载中，或者该项是当前 head，则禁用点击
                                disabled={isLoading}
                            >
                                <ListItemIcon sx={{ minWidth: 32 }}>
                                    {isHead ? <RadioButtonCheckedIcon color="primary" fontSize="small" /> : <RadioButtonUncheckedIcon fontSize="small" />}
                                </ListItemIcon>
                                <ListItemText
                                    primary={summary}
                                    secondary={timestamp}
                                    primaryTypographyProps={{ noWrap: true, variant: 'body2', fontWeight: isHead ? 'bold' : 'normal' }}
                                    secondaryTypographyProps={{ noWrap: true, variant: 'caption' }}
                                />
                            </ListItemButton>
                        </ListItem>
                    );
                })}
            </List>
        </>
    );

    return (
        <Drawer
            sx={{
                width: width,
                flexShrink: 0,
                '& .MuiDrawer-paper': {
                    width: width,
                    boxSizing: 'border-box',
                    display: 'flex',
                    flexDirection: 'column',
                },
            }}
            anchor="left"
            {...drawerProps}
        >
            {drawerContent}
        </Drawer>
    );
};