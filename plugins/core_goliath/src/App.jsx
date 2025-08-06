import React, { useState, useEffect } from 'react';

// MUI 组件
import {
    AppBar, Box, CssBaseline, Drawer, Toolbar, Typography, List, ListItem, ListItemButton,
    ListItemIcon, ListItemText, Divider, Dialog, DialogTitle, DialogContent,
    DialogContentText, DialogActions, Button
} from '@mui/material';

// MUI 图标
import InboxIcon from '@mui/icons-material/MoveToInbox';
import MailIcon from '@mui/icons-material/Mail';

// 从平台获取服务的钩子
import { useService } from './hooks/useService';

const drawerWidth = 240;

export function App() {
    const hookManager = useService('hookManager');
    const [aboutDialogOpen, setAboutDialogOpen] = useState(false);

    useEffect(() => {
        if (!hookManager) return;
        
        // 定义命令处理器
        const showDialog = () => setAboutDialogOpen(true);
        
        // 监听由命令触发的钩子
        hookManager.addImplementation('ui.show.aboutDialog', showDialog);

        // 清理函数
        return () => {
            hookManager.removeImplementation('ui.show.aboutDialog', showDialog);
        };
    }, [hookManager]);

    const handleCloseAboutDialog = () => {
        setAboutDialogOpen(false);
    };

    return (
        <Box sx={{ display: 'flex' }}>
            {/* CssBaseline 提供了基础的样式重置和MUI主题背景 */}
            <CssBaseline />
            
            <AppBar
                position="fixed"
                sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
            >
                <Toolbar>
                    <Typography variant="h6" noWrap component="div">
                        Hevno Engine (Goliath UI)
                    </Typography>
                </Toolbar>
            </AppBar>

            <Drawer
                variant="permanent"
                sx={{
                    width: drawerWidth,
                    flexShrink: 0,
                    [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
                }}
            >
                <Toolbar />
                <Box sx={{ overflow: 'auto' }}>
                    <List>
                        {['Sandboxes', 'History', 'Assets'].map((text, index) => (
                            <ListItem key={text} disablePadding>
                                <ListItemButton>
                                    <ListItemIcon>
                                        {index % 2 === 0 ? <InboxIcon /> : <MailIcon />}
                                    </ListItemIcon>
                                    <ListItemText primary={text} />
                                </ListItemButton>
                            </ListItem>
                        ))}
                    </List>
                    <Divider />
                </Box>
            </Drawer>

            <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
                <Toolbar />
                <Typography variant="h4" gutterBottom>
                    Welcome to the Hevno Engine!
                </Typography>
                <Typography paragraph>
                    This is the main content area. All primary views and editors will be rendered here.
                </Typography>
                <Typography paragraph>
                    The UI is successfully rendered by the <strong>core_goliath</strong> plugin using React and Material-UI.
                </Typography>
                 <Button variant="contained" onClick={() => hookManager.trigger('ui.show.aboutDialog')}>
                    Test 'About' Dialog
                </Button>
            </Box>

            {/* "About" 对话框 */}
            <Dialog open={aboutDialogOpen} onClose={handleCloseAboutDialog}>
                <DialogTitle>About Hevno Engine</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        This dialog was triggered by a command registered by the Goliath plugin.
                        This demonstrates the full loop: Command - Hook - React State Change - UI Update.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseAboutDialog}>Close</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}