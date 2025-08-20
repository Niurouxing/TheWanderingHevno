// plugins/core_runner_ui/src/components/ManagementPanel.jsx
import React from 'react';
import { 
    Box, Paper, Typography, Button, List, ListItem, ListItemText, ListItemIcon, Switch, Divider 
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import RestartAltIcon from '@mui/icons-material/RestartAlt';

export function ManagementPanel({ 
    isOpen, 
    onClose, 
    availablePanels, 
    activePanelIds, 
    onTogglePanel,
    onResetLayout
}) {
    if (!isOpen) return null;

    return (
        <Box 
            sx={{ 
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, 
                bgcolor: 'rgba(0,0,0,0.8)', zIndex: 10,
                backdropFilter: 'blur(5px)',
                display: 'flex', justifyContent: 'center', alignItems: 'center'
            }}
            onClick={onClose}
        >
            <Paper 
                elevation={10}
                sx={{ 
                    width: 'clamp(350px, 50vw, 500px)', 
                    maxHeight: '80vh',
                    display: 'flex',
                    flexDirection: 'column',
                    p: 2,
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">驾驶舱管理</Typography>
                    <Button onClick={onClose}>关闭</Button>
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    控制在驾驶舱中显示哪些面板。布局会自动保存。
                </Typography>

                <List sx={{ overflowY: 'auto', flexGrow: 1 }}>
                    {availablePanels.map(panel => {
                        const isActive = activePanelIds.includes(panel.id);
                        return (
                            <ListItem key={panel.id} secondaryAction={
                                <Switch
                                    edge="end"
                                    onChange={() => onTogglePanel(panel.id)}
                                    checked={isActive}
                                />
                            }>
                                <ListItemIcon>
                                    {isActive ? <VisibilityIcon /> : <VisibilityOffIcon color="disabled"/>}
                                </ListItemIcon>
                                <ListItemText primary={panel.name} />
                            </ListItem>
                        );
                    })}
                </List>

                <Divider sx={{ my: 2 }} />

                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button 
                        variant="outlined" 
                        color="warning" 
                        startIcon={<RestartAltIcon />}
                        onClick={onResetLayout}
                    >
                        重置布局
                    </Button>
                </Box>
            </Paper>
        </Box>
    );
}
