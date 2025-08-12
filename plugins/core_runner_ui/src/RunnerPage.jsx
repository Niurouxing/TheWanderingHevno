// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Box, Typography, CircularProgress, Alert, Paper, IconButton, Collapse } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { ConversationStream } from './components/ConversationStream';
import { UserInputBar } from './components/UserInputBar';
// [修改] 从 api.js 导入所有需要的函数
import { query, mutate, step, getHistory, revert } from './api';
import BugReportIcon from '@mui/icons-material/BugReport';

export function RunnerPage() {
    const { currentSandboxId } = useLayout();
    
    // [新] 状态管理重构
    const [snapshotHistory, setSnapshotHistory] = useState([]); // 存储完整的快照历史
    const [initialInputText, setInitialInputText] = useState(''); // 用于编辑后重新提交
    
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState(null);
    const [showDiagnostics, setShowDiagnostics] = useState(false);
    
    const conversationEndRef = useRef(null);
    
    const scrollToBottom = () => {
        conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // [新] 使用 useMemo 从快照历史中派生出用于显示的消息列表
    const messages = useMemo(() => {
        const allMessages = [];
        for (const snapshot of snapshotHistory) {
            const entries = snapshot.moment?.memoria?.chat_history?.entries || [];
            for (const entry of entries) {
                // 为每个消息附加其所在的快照信息
                allMessages.push({ ...entry, snapshot_id: snapshot.id, parent_snapshot_id: snapshot.parent_snapshot_id, triggering_input: snapshot.triggering_input });
            }
        }
        // 去重，因为 memoria 是累积的
        const uniqueMessages = Array.from(new Map(allMessages.map(item => [item.id, item])).values());
        uniqueMessages.sort((a, b) => a.sequence_id - b.sequence_id);
        return uniqueMessages;
    }, [snapshotHistory]);

    // [修改] loadData 函数现在获取完整的历史记录
    const loadData = useCallback(async () => {
        if (!currentSandboxId) return;
        setIsLoading(true);
        setError('');
        try {
            const history = await getHistory(currentSandboxId);
            setSnapshotHistory(history);
        } catch (e) {
            setError(`Failed to load sandbox history: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    }, [currentSandboxId]);

    useEffect(() => {
        loadData();
    }, [loadData]);
    
    useEffect(scrollToBottom, [messages]); // 依赖于派生出的 messages

    // [重构] 主提交逻辑
    const handleUserSubmit = async (inputText) => {
        if (!currentSandboxId || isLoading) return;

        setIsLoading(true);
        setError('');
        setDiagnostics(null);
        setInitialInputText(''); // 提交后清空编辑状态

        try {
            // 注意: `revert` 逻辑现在在 `handleEdit` 中处理
            await mutate(currentSandboxId, [{
                type: 'UPSERT',
                path: 'moment/_user_input',
                value: inputText
            }]);

            const stepResponse = await step(currentSandboxId, { /* `user_input` 已经在 moment 中 */ });
            
            if (stepResponse.status === 'ERROR') {
                throw new Error(stepResponse.error_message || "An unknown error occurred during step execution.");
            }
            if(stepResponse.diagnostics) {
                setDiagnostics(stepResponse.diagnostics);
            }
            
            // 成功后，重新加载整个历史以确保状态一致
            await loadData();

        } catch (e) {
            setError(e.message);
            await loadData(); // 即使失败也刷新状态，以移除乐观更新
        } finally {
            setIsLoading(false);
        }
    };
    
    // [新增] 处理重新生成请求
    const handleRegenerate = async (message) => {
        if (!currentSandboxId || isLoading || !message.parent_snapshot_id) return;
        
        setIsLoading(true);
        setError('');
        setDiagnostics(null);
        
        try {
            // 回滚到AI生成此消息【之前】的快照
            await revert(currentSandboxId, message.parent_snapshot_id);
            
            // 使用【当时】的触发输入再次执行 step
            const stepResponse = await step(currentSandboxId, message.triggering_input || {});

            if (stepResponse.status === 'ERROR') {
                throw new Error(stepResponse.error_message || "An unknown error occurred during regeneration.");
            }
             if(stepResponse.diagnostics) {
                setDiagnostics(stepResponse.diagnostics);
            }

            await loadData();
        } catch(e) {
            setError(e.message);
        } finally {
            setIsLoading(false);
        }
    };
    
    // [新增] 处理编辑请求
    const handleEdit = async (message) => {
        if (!currentSandboxId || isLoading || !message.parent_snapshot_id) return;

        setIsLoading(true);
        setError('');
        setDiagnostics(null);

        try {
            // 回滚到你发送此消息【之前】的快照
            await revert(currentSandboxId, message.parent_snapshot_id);
            // 重新加载历史，UI会移除被回滚的消息
            await loadData(); 
            // 将你的旧消息填充到输入框
            setInitialInputText(message.content);
        } catch (e) {
            setError(e.message);
        } finally {
            setIsLoading(false);
        }
    };


    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h5">请开始</Typography>
                <Typography color="text.secondary">
                  从 "沙盒列表" 页面选择一个沙盒以开始交互。
                </Typography>
            </Box>
        );
    }
    
    if (isLoading && snapshotHistory.length === 0) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: { xs: 1, sm: 2 } }}>
            <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2 }}>
                {/* [修改] 传递新的处理器 */}
                <ConversationStream messages={messages} onRegenerate={handleRegenerate} onEdit={handleEdit} />
                <div ref={conversationEndRef} />
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
                    {/* [修改] 传递新的 initialText */}
                    <UserInputBar onSendMessage={handleUserSubmit} isLoading={isLoading} initialText={initialInputText} />
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', pt: 1}}>
                        {diagnostics && (
                             <IconButton size="small" onClick={() => setShowDiagnostics(s => !s)} title="显示/隐藏诊断信息">
                                <BugReportIcon color={showDiagnostics ? "primary" : "inherit"} />
                             </IconButton>
                        )}
                    </Box>
                </Paper>
            </Box>
        </Box>
    );
}

export default RunnerPage;