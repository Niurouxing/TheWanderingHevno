// plugins/core_runner_ui/src/components/SnapshotHistoryDrawer.jsx
import React from 'react';
import { 
    Drawer, List, ListItem, ListItemButton, ListItemText, ListItemIcon, 
    Tooltip, Box, Typography, IconButton, Divider, Toolbar, Skeleton
} from '@mui/material';
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import HistoryToggleOffIcon from '@mui/icons-material/HistoryToggleOff';

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

// [FIX] Added the 'export' keyword to make the component importable
export const SnapshotHistoryDrawer = ({ history, headSnapshotId, onRevert, isLoading, width, ...drawerProps }) => {
    
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
                                !isHead && (
                                    <Tooltip title="切换到此状态">
                                        <span> {/* Tooltip wrapper for disabled button */}
                                            <IconButton edge="end" onClick={() => onRevert(snapshot.id)} disabled={isLoading}>
                                                <HistoryToggleOffIcon />
                                            </IconButton>
                                        </span>
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