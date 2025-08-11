import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Typography, CircularProgress, Alert, Paper, IconButton, Collapse } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { ConversationStream } from './components/ConversationStream';
import { UserInputBar } from './components/UserInputBar';
import { query, mutate, step } from './api';
import BugReportIcon from '@mui/icons-material/BugReport';

export function RunnerPage() {
    const { currentSandboxId } = useLayout();
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [diagnostics, setDiagnostics] = useState(null);
    const [showDiagnostics, setShowDiagnostics] = useState(false);
    
    // 用于自动滚动
    const conversationEndRef = useRef(null);
    
    const scrollToBottom = () => {
        conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const loadHistory = useCallback(async () => {
        if (!currentSandboxId) return;
        setIsLoading(true);
        setError('');
        try {
            const data = await query(currentSandboxId, ['moment.memoria.chat_history.entries']);
            const history = data['moment.memoria.chat_history.entries'] || [];
            setMessages(history);
        } catch (e) {
            setError(`Failed to load chat history: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    }, [currentSandboxId]);

    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    const handleUserSubmit = async (inputText) => {
        if (!currentSandboxId) {
            setError("No sandbox selected.");
            return;
        }

        setIsLoading(true);
        setError('');
        setDiagnostics(null);

        // 乐观地显示用户消息
        const userMessage = {
            id: `user_${Date.now()}`,
            level: 'user',
            content: inputText,
            created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, userMessage]);

        try {
            // 1. Mutate: 写入用户输入
            await mutate(currentSandboxId, [{
                type: 'UPSERT',
                path: 'moment.__input__',
                value: inputText
            }]);

            // 2. Step: 触发后端计算
            const stepResponse = await step(currentSandboxId, {});
            
            if (stepResponse.status === 'ERROR') {
                throw new Error(stepResponse.error_message || "An unknown error occurred during step execution.");
            }
            if(stepResponse.diagnostics) {
                setDiagnostics(stepResponse.diagnostics);
            }

            // 3. Query: 获取更新后的聊天记录
            const data = await query(currentSandboxId, ['moment.memoria.chat_history.entries']);
            const newHistory = data['moment.memoria.chat_history.entries'] || [];
            setMessages(newHistory);

        } catch (e) {
            setError(e.message);
            // 如果出错，移除乐观显示的消息
            setMessages(prev => prev.filter(msg => msg.id !== userMessage.id));
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
    
    if (isLoading && messages.length === 0) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
    }

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: { xs: 1, sm: 2 } }}>
            <Box sx={{ flexGrow: 1, overflowY: 'auto', mb: 2 }}>
                <ConversationStream messages={messages} />
                <div ref={conversationEndRef} />
            </Box>
            
            <Box sx={{ flexShrink: 0 }}>
                {error && <Alert severity="error" sx={{ mb: 1.5 }}>{error}</Alert>}

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
        </Box>
    );
}

export default RunnerPage;