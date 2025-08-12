// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
    Box, Typography, CircularProgress, Alert, Paper, IconButton, Collapse, CssBaseline,
    AppBar, Toolbar, Tooltip, useTheme, useMediaQuery
} from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { ConversationStream } from './components/ConversationStream';
import { UserInputBar } from './components/UserInputBar';
import { SnapshotHistoryDrawer } from './components/SnapshotHistoryDrawer'; // 重命名为 Drawer
import { getSandboxDetails, mutate, step, getHistory, revert } from './api';
import BugReportIcon from '@mui/icons-material/BugReport';
import MenuIcon from '@mui/icons-material/Menu';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

const DRAWER_WIDTH = 320; // 定义侧边栏宽度

export function RunnerPage() {
    const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
    const theme = useTheme();
    const isLargeScreen = useMediaQuery(theme.breakpoints.up('md'));

    const [sandboxDetails, setSandboxDetails] = useState(null);
    const [snapshotHistory, setSnapshotHistory] = useState([]);
    const [headSnapshotId, setHeadSnapshotId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState(null);
    const [showDiagnostics, setShowDiagnostics] = useState(false);
    const [isHistoryDrawerOpen, setHistoryDrawerOpen] = useState(isLargeScreen);

    // 监听屏幕尺寸变化以调整侧边栏状态
    useEffect(() => {
        setHistoryDrawerOpen(isLargeScreen);
    }, [isLargeScreen]);
    
    // 提取消息列表的 useMemo 逻辑保持不变
    const messages = useMemo(() => {
        const allMessages = [];
        const headPath = new Map();
        let currentId = headSnapshotId;
        while(currentId) {
            const snapshot = snapshotHistory.find(s => s.id === currentId);
            if(snapshot) {
                headPath.set(snapshot.id, snapshot);
                currentId = snapshot.parent_snapshot_id;
            } else {
                break;
            }
        }
        for (const snapshot of [...snapshotHistory].reverse()) {
            if (headPath.has(snapshot.id)) {
                const entries = snapshot.moment?.memoria?.chat_history?.entries || [];
                for (const entry of entries) {
                    allMessages.push({ ...entry, snapshot_id: snapshot.id, parent_snapshot_id: snapshot.parent_snapshot_id, triggering_input: snapshot.triggering_input });
                }
            }
        }
        const uniqueMessages = Array.from(new Map(allMessages.map(item => [item.id, item])).values());
        uniqueMessages.sort((a, b) => a.sequence_id - b.sequence_id);
        return uniqueMessages;
    }, [snapshotHistory, headSnapshotId]);


    const loadData = useCallback(async (showLoading = true) => {
        if (!currentSandboxId) return;
        if (showLoading) setIsLoading(true);
        setError('');
        try {
            const [history, details] = await Promise.all([
                getHistory(currentSandboxId),
                getSandboxDetails(currentSandboxId)
            ]);
            
            if (!details || !details.head_snapshot_id) {
                 throw new Error("Retrieved sandbox details are incomplete.");
            }
            
            setSnapshotHistory(history);
            setSandboxDetails(details);
            setHeadSnapshotId(details.head_snapshot_id);

        } catch (e) {
            setError(`Failed to load sandbox data: ${e.message}`);
        } finally {
            if (showLoading) setIsLoading(false);
        }
    }, [currentSandboxId]);

    useEffect(() => {
        if (currentSandboxId) {
            loadData();
        } else {
            // 如果没有沙盒ID，清空所有状态
            setSandboxDetails(null);
            setSnapshotHistory([]);
            setHeadSnapshotId(null);
            setError('');
        }
    }, [currentSandboxId, loadData]);
    
    const handleUserSubmit = async (inputText) => {
        if (!currentSandboxId || isLoading) return;
        setIsLoading(true);
        setError('');
        setDiagnostics(null);
        try {
            await mutate(currentSandboxId, [{ type: 'UPSERT', path: 'moment/_user_input', value: inputText }]);
            const stepResponse = await step(currentSandboxId, {});
            if (stepResponse.status === 'ERROR') throw new Error(stepResponse.error_message);
            if (stepResponse.diagnostics) setDiagnostics(stepResponse.diagnostics);
            await loadData(false); 
        } catch (e) {
            setError(e.message);
            await loadData(false);
        } finally {
            setIsLoading(false);
        }
    };
    
    const handleRegenerate = async (message) => {
        if (!currentSandboxId || isLoading || !message.parent_snapshot_id) return;
        setIsLoading(true);
        setError('');
        setDiagnostics(null);
        try {
            await revert(currentSandboxId, message.parent_snapshot_id);
            const stepResponse = await step(currentSandboxId, message.triggering_input || {});
            if (stepResponse.status === 'ERROR') throw new Error(stepResponse.error_message);
            if (stepResponse.diagnostics) setDiagnostics(stepResponse.diagnostics);
            await loadData(false);
        } catch(e) {
            setError(e.message);
        } finally {
            setIsLoading(false);
        }
    };
    
    const handleEditSubmit = async (message, newContent) => {
        if (!currentSandboxId || isLoading || !message.parent_snapshot_id) return;
        setIsLoading(true);
        setError('');
        setDiagnostics(null);
        try {
            await revert(currentSandboxId, message.parent_snapshot_id);
            await mutate(currentSandboxId, [{ type: 'UPSERT', path: 'moment/_user_input', value: newContent }]);
            const stepResponse = await step(currentSandboxId, {});
            if (stepResponse.status === 'ERROR') throw new Error(stepResponse.error_message);
            if (stepResponse.diagnostics) setDiagnostics(stepResponse.diagnostics);
            await loadData(false);
        } catch (e) {
            setError(e.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRevert = async (snapshotId) => {
        if (!currentSandboxId || isLoading) return;
        setIsLoading(true);
        setError('');
        try {
            await revert(currentSandboxId, snapshotId);
            await loadData(false);
        } catch (e) {
            setError(`Failed to revert: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoBackToExplorer = () => {
        setCurrentSandboxId(null);
        setActivePageId('sandbox_explorer.main_view');
    };

    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h5">开始交互</Typography>
                <Typography color="text.secondary">请从 "沙盒列表" 页面选择一个沙盒以开始。</Typography>
            </Box>
        );
    }
    
    return (
        <Box sx={{ display: 'flex', height: '100vh', width: '100vw' }}>
            <CssBaseline />
            <SnapshotHistoryDrawer 
                history={snapshotHistory} 
                headSnapshotId={headSnapshotId} 
                onRevert={handleRevert} 
                isLoading={isLoading}
                open={isHistoryDrawerOpen}
                onClose={() => setHistoryDrawerOpen(false)}
                variant={isLargeScreen ? 'persistent' : 'temporary'}
                width={DRAWER_WIDTH}
            />

            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    height: '100%',
                    transition: theme.transitions.create('margin', {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.leavingScreen,
                    }),
                    marginLeft: `-${DRAWER_WIDTH}px`, // 默认隐藏
                    ...(isHistoryDrawerOpen && { // 当打开时
                        transition: theme.transitions.create('margin', {
                            easing: theme.transitions.easing.easeOut,
                            duration: theme.transitions.duration.enteringScreen,
                        }),
                        marginLeft: 0,
                    }),
                }}
            >
                <AppBar position="static" color="default" sx={{ boxShadow: 'none', borderBottom: 1, borderColor: 'divider' }}>
                    <Toolbar>
                        <Tooltip title="切换历史记录">
                            <IconButton
                                color="inherit"
                                aria-label="open drawer"
                                onClick={() => setHistoryDrawerOpen(!isHistoryDrawerOpen)}
                                edge="start"
                                sx={{ mr: 2 }}
                            >
                                <MenuIcon />
                            </IconButton>
                        </Tooltip>
                        <Tooltip title="返回沙盒列表">
                             <IconButton
                                color="inherit"
                                onClick={handleGoBackToExplorer}
                                edge="start"
                            >
                                <ArrowBackIcon />
                            </IconButton>
                        </Tooltip>
                        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, ml: 1 }}>
                            {sandboxDetails?.name || 'Loading...'}
                        </Typography>
                        {diagnostics && (
                            <Tooltip title="显示/隐藏诊断信息">
                                <IconButton size="small" onClick={() => setShowDiagnostics(s => !s)}>
                                    <BugReportIcon color={showDiagnostics ? "primary" : "inherit"} />
                                </IconButton>
                            </Tooltip>
                        )}
                    </Toolbar>
                </AppBar>

                <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                    {isLoading && snapshotHistory.length === 0 ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
                    ) : (
                        <ConversationStream 
                            messages={messages} 
                            onRegenerate={handleRegenerate} 
                            onEditSubmit={handleEditSubmit}
                        />
                    )}
                </Box>
                
                <Box sx={{ flexShrink: 0, p: { xs: 1, sm: 2 } }}>
                    {error && <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setError('')}>{error}</Alert>}
                    <Collapse in={showDiagnostics}>
                        <Paper variant="outlined" sx={{ p: 2, mb: 1.5, maxHeight: 200, overflowY: 'auto', bgcolor: 'background.default' }}>
                            <Typography variant="subtitle2">诊断信息</Typography>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.8rem' }}>
                                {JSON.stringify(diagnostics, null, 2)}
                            </pre>
                        </Paper>
                    </Collapse>
                    <UserInputBar onSendMessage={handleUserSubmit} isLoading={isLoading} />
                </Box>
            </Box>
        </Box>
    );
}

export default RunnerPage;