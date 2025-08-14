// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { 
    Box, Typography, CircularProgress, Alert, Paper, IconButton, Collapse, CssBaseline,
    AppBar, Toolbar, Tooltip, useTheme, useMediaQuery
} from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { ConversationStream } from './components/ConversationStream';
import { UserInputBar } from './components/UserInputBar';
import { SnapshotHistoryDrawer } from './components/SnapshotHistoryDrawer';
import { getSandboxDetails, mutate, step, getHistory, revert, deleteSnapshot, resetHistory } from './api';
import BugReportIcon from '@mui/icons-material/BugReport';
import MenuIcon from '@mui/icons-material/Menu';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddCommentIcon from '@mui/icons-material/AddComment';

const DRAWER_WIDTH = 320;

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
    const [diagnosticsHeight, setDiagnosticsHeight] = useState(200);
    const resizeRef = useRef(null);

    const [optimisticMessage, setOptimisticMessage] = useState(null);

    const handleResizeMouseDown = useCallback((e) => {
        e.preventDefault();
        resizeRef.current = {
            initialHeight: diagnosticsHeight,
            initialY: e.clientY,
        };
        document.addEventListener('mousemove', handleResizeMouseMove);
        document.addEventListener('mouseup', handleResizeMouseUp);
    }, [diagnosticsHeight]);

    const handleResizeMouseMove = useCallback((e) => {
        if (!resizeRef.current) return;
        const { initialHeight, initialY } = resizeRef.current;
        const dy = e.clientY - initialY;
        const newHeight = initialHeight - dy;
        const clampedHeight = Math.max(50, Math.min(newHeight, 600));
        setDiagnosticsHeight(clampedHeight);
    }, []);

    const handleResizeMouseUp = useCallback(() => {
        resizeRef.current = null;
        document.removeEventListener('mousemove', handleResizeMouseMove);
        document.removeEventListener('mouseup', handleResizeMouseUp);
    }, []);

    useEffect(() => {
        setHistoryDrawerOpen(isLargeScreen);
    }, [isLargeScreen]);
    
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
        let uniqueMessages = Array.from(new Map(allMessages.map(item => [item.id, item])).values());
        uniqueMessages.sort((a, b) => a.sequence_id - b.sequence_id);

        if (optimisticMessage) {
            uniqueMessages.push(optimisticMessage);
        }

        return uniqueMessages;
    }, [snapshotHistory, headSnapshotId, optimisticMessage]);


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
            setSandboxDetails(null);
            setSnapshotHistory([]);
            setHeadSnapshotId(null);
            setError('');
        }
    }, [currentSandboxId, loadData]);
    
    const handleUserSubmit = async (inputText) => {
        if (!currentSandboxId || isLoading) return;
        
        const tempMsg = {
            id: `optimistic_${Date.now()}`,
            content: inputText,
            level: 'user',
            sequence_id: (messages.length > 0 ? messages[messages.length - 1].sequence_id : 0) + 1,
        };
        setOptimisticMessage(tempMsg);
        
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
            setOptimisticMessage(null);
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
    
    const handleDeleteSnapshot = async (snapshotId) => {
        if (!currentSandboxId || isLoading || snapshotId === headSnapshotId) return;
        if (window.confirm("确定要永久删除这个历史记录点吗？")) {
            setIsLoading(true);
            setError('');
            try {
                await deleteSnapshot(currentSandboxId, snapshotId);
                await loadData(false);
            } catch (e) {
                setError(`删除失败: ${e.message}`);
            } finally {
                setIsLoading(false);
            }
        }
    };

    const handleResetHistory = async () => {
        if (!currentSandboxId || isLoading) return;
        if (window.confirm("确定要开启一个新的会话吗？当前会话将成为历史记录。")) {
            setIsLoading(true);
            setError('');
            try {
                await resetHistory(currentSandboxId);
                await loadData(false);
            } catch (e) {
                setError(`开启新会话失败: ${e.message}`);
            } finally {
                setIsLoading(false);
            }
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
                onDelete={handleDeleteSnapshot}
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
                    marginLeft: `-${DRAWER_WIDTH}px`,
                    ...(isHistoryDrawerOpen && {
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
                            <IconButton color="inherit" aria-label="open drawer" onClick={() => setHistoryDrawerOpen(!isHistoryDrawerOpen)} edge="start" sx={{ mr: 2 }}>
                                <MenuIcon />
                            </IconButton>
                        </Tooltip>
                        <Tooltip title="返回沙盒列表">
                             <IconButton color="inherit" onClick={handleGoBackToExplorer} edge="start">
                                <ArrowBackIcon />
                            </IconButton>
                        </Tooltip>
                        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, ml: 1 }}>
                            {sandboxDetails?.name || 'Loading...'}
                        </Typography>
                        
                        <Tooltip title="新建会话">
                            <IconButton size="small" onClick={handleResetHistory} disabled={isLoading}>
                                <AddCommentIcon />
                            </IconButton>
                        </Tooltip>

                        {diagnostics && (
                            <Tooltip title="显示/隐藏诊断信息">
                                <IconButton size="small" onClick={() => setShowDiagnostics(s => !s)} sx={{ ml: 1 }}>
                                    <BugReportIcon color={showDiagnostics ? "primary" : "inherit"} />
                                </IconButton>
                            </Tooltip>
                        )}
                    </Toolbar>
                </AppBar>

                <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                    {isLoading && messages.length === 0 && !optimisticMessage ? (
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
                        <Paper 
                            variant="outlined" 
                            sx={{ p: 2, pt: 3, mb: 1.5, height: diagnosticsHeight, overflow: 'hidden', bgcolor: 'background.default', position: 'relative', display: 'flex', flexDirection: 'column' }}
                        >
                            <Box onMouseDown={handleResizeMouseDown} sx={{ position: 'absolute', top: 0, left: 0, right: 0, height: '10px', cursor: 'ns-resize', display: 'flex', alignItems: 'center', justifyContent: 'center', '&:hover div': { backgroundColor: theme.palette.action.active, }}}>
                                 <Box sx={{ width: '40px', height: '4px', backgroundColor: theme.palette.divider, borderRadius: '2px', transition: 'background-color 0.2s' }} />
                            </Box>
                            <Typography variant="subtitle2" sx={{ flexShrink: 0 }}>诊断信息</Typography>
                            <pre style={{ flexGrow: 1, margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.8rem', overflowY: 'auto' }}>
                                {JSON.stringify(diagnostics, null, 2)}
                            </pre>
                        </Paper>
                    </Collapse>
                    {/* [修复] 恢复正确的 isLoading 逻辑 */}
                    <UserInputBar onSendMessage={handleUserSubmit} isLoading={isLoading} />
                </Box>
            </Box>
        </Box>
    );
}

export default RunnerPage;