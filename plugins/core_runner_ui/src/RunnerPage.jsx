// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Typography, CircularProgress, Alert, Paper, IconButton, Collapse, Grid } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { ConversationStream } from './components/ConversationStream';
import { UserInputBar } from './components/UserInputBar';
import { SnapshotHistory } from './components/SnapshotHistory'; 
// [修改] 导入 getSandboxDetails
import { getSandboxDetails, mutate, step, getHistory, revert } from './api';
import BugReportIcon from '@mui/icons-material/BugReport';

export function RunnerPage() {
    const { currentSandboxId } = useLayout();
    
    // ... (状态和 useMemo 逻辑不变) ...
    const [snapshotHistory, setSnapshotHistory] = useState([]);
    const [headSnapshotId, setHeadSnapshotId] = useState(null); 
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState(null);
    const [showDiagnostics, setShowDiagnostics] = useState(false);
    
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


    // --- 数据加载与核心逻辑 ---
    const loadData = useCallback(async (showLoading = true) => {
        if (!currentSandboxId) return;
        if (showLoading) setIsLoading(true);
        setError('');
        try {
            // --- [修复开始] ---
            // 使用新的、更直接的 API 调用方式
            const [history, sandboxDetails] = await Promise.all([
                getHistory(currentSandboxId),
                getSandboxDetails(currentSandboxId) 
            ]);
            // --- [修复结束] ---
            
            if (!sandboxDetails || !sandboxDetails.head_snapshot_id) {
                 // 这个错误现在意味着 getSandboxDetails 成功了，但返回的对象缺少关键字段
                 throw new Error("Retrieved sandbox details are incomplete.");
            }
            
            setSnapshotHistory(history);
            setHeadSnapshotId(sandboxDetails.head_snapshot_id);

        } catch (e) {
            setError(`Failed to load sandbox data: ${e.message}`);
        } finally {
            if (showLoading) setIsLoading(false);
        }
    }, [currentSandboxId]);

    useEffect(() => {
        loadData();
    }, [loadData]);
    
    // ... (事件处理器和渲染逻辑无变化) ...
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

    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h5">请开始</Typography>
                <Typography color="text.secondary">从 "沙盒列表" 页面选择一个沙盒以开始交互。</Typography>
            </Box>
        );
    }
    
    if (isLoading && snapshotHistory.length === 0) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
    }

    return (
        <Grid container sx={{ height: '100%', p: { xs: 1, sm: 2 } }} spacing={2}>
            {/* 左侧：快照历史 */}
            <Grid item xs={12} md={4} lg={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h6" sx={{ mb: 1, px: 1, flexShrink: 0 }}>交互历史</Typography>
                <Paper variant="outlined" sx={{ flexGrow: 1, overflowY: 'auto' }}>
                    <SnapshotHistory 
                        history={snapshotHistory} 
                        headSnapshotId={headSnapshotId} 
                        onRevert={handleRevert} 
                        isLoading={isLoading}
                    />
                </Paper>
            </Grid>

            {/* 右侧：对话流和输入 */}
            <Grid item xs={12} md={8} lg={9} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2 }}>
                    <ConversationStream 
                        messages={messages} 
                        onRegenerate={handleRegenerate} 
                        onEditSubmit={handleEditSubmit}
                    />
                </Box>
                
                <Box sx={{ flexShrink: 0 }}>
                    {error && <Alert severity="error" sx={{ mb: 1.5 }} onClose={() => setError('')}>{error}</Alert>}
                    <Collapse in={showDiagnostics}>
                        <Paper variant="outlined" sx={{ p: 2, mb: 1.5, maxHeight: 200, overflowY: 'auto' }}>
                            <Typography variant="subtitle2">诊断信息</Typography>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                                {JSON.stringify(diagnostics, null, 2)}
                            </pre>
                        </Paper>
                    </Collapse>

                    <Paper variant="outlined" sx={{ p: 1.5 }}>
                        <UserInputBar onSendMessage={handleUserSubmit} isLoading={isLoading} />
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', pt: 1}}>
                            {diagnostics && (
                                <IconButton size="small" onClick={() => setShowDiagnostics(s => !s)} title="显示/隐藏诊断信息">
                                    <BugReportIcon color={showDiagnostics ? "primary" : "inherit"} />
                                </IconButton>
                            )}
                        </Box>
                    </Paper>
                </Box>
            </Grid>
        </Grid>
    );
}

export default RunnerPage;