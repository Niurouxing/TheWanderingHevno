// plugins/core_runner_ui/src/components/ManagementPanel.jsx
import React from 'react';
import { 
    Box, Paper, Typography, Button, List, ListItem, ListItemText, Switch, Divider,
    ListSubheader, RadioGroup, FormControlLabel, Radio
} from '@mui/material';
import RestartAltIcon from '@mui/icons-material/RestartAlt';

export function ManagementPanel({ 
    isOpen, 
    onClose, 
    // [新功能] 接收背景和面板两种类型的组件
    availableBackgrounds,
    activeBackgroundId,
    onSelectBackground,
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
                    width: 'clamp(400px, 50vw, 550px)', 
                    maxHeight: '80vh',
                    display: 'flex',
                    flexDirection: 'column',
                    p: 2.5,
                }}
                onClick={(e) => e.stopPropagation()}
            >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">驾驶舱管理</Typography>
                    <Button onClick={onClose}>关闭</Button>
                </Box>

                <List sx={{ overflowY: 'auto', flexGrow: 1, p:0 }}>
                    {/* --- 背景画布选择区 --- */}
                    <ListSubheader sx={{bgcolor: 'transparent'}}>背景画布 (单选)</ListSubheader>
                    <RadioGroup
                        aria-label="background-selector"
                        name="background-selector"
                        value={activeBackgroundId || 'none'}
                        onChange={(e) => onSelectBackground(e.target.value === 'none' ? null : e.target.value)}
                    >
                        <ListItem>
                             <FormControlLabel value="none" control={<Radio />} label="无" />
                        </ListItem>
                        {availableBackgrounds.map(bg => (
                            <ListItem key={bg.id}>
                                <FormControlLabel value={bg.id} control={<Radio />} label={bg.name} />
                            </ListItem>
                        ))}
                    </RadioGroup>

                    <Divider sx={{ my: 1.5 }} />

                    {/* --- 浮动面板选择区 --- */}
                    <ListSubheader sx={{bgcolor: 'transparent'}}>浮动面板 (多选)</ListSubheader>
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
