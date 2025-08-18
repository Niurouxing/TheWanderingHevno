// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useEffect, useState } from 'react';
import { Box, Typography, CssBaseline, AppBar, Toolbar, Tooltip, IconButton } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { CircularProgress, Alert } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';

import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { CockpitLayout } from './components/CockpitLayout';
import { UserInputBar } from './components/UserInputBar';

// 将内部内容分离出来，以便能访问到 Context
function CockpitContent() {
    const { isStepping, error, performStep, isLoading, moment } = useSandboxState();
    
    // 如果初次加载时没有 moment 数据，显示加载动画
    if (isLoading && !moment) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
    }
    
    const handleUserSubmit = async (inputText) => {
        const payload = { user_message: inputText };
        await performStep(payload);
    };

    return (
        <>
            <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 1 }}>
                <CockpitLayout />
            </Box>
            <Box sx={{ flexShrink: 0, p: { xs: 1, sm: 2 } }}>
                 {error && <Alert severity="error" sx={{ mb: 1.5 }}>{error}</Alert>}
                <UserInputBar onSendMessage={handleUserSubmit} isLoading={isStepping} />
            </Box>
        </>
    );
}


export function RunnerPage({ services }) {
    const { currentSandboxId, setActivePageId, setCurrentSandboxId } = useLayout();
    // 暂时从 services 中获取沙盒详情，实际可以合并到 SandboxStateProvider 中
    const [sandboxName, setSandboxName] = useState('Loading...'); 

    useEffect(() => {
        // 简单的获取沙盒名称逻辑
        const fetchName = async () => {
            if (!currentSandboxId) return;
            try {
                const res = await fetch(`/api/sandboxes/${currentSandboxId}`);
                const data = await res.json();
                setSandboxName(data.name);
            } catch {
                setSandboxName('Unknown Sandbox');
            }
        };
        fetchName();
    }, [currentSandboxId]);

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
        <SandboxStateProvider sandboxId={currentSandboxId}>
            <Box sx={{ display: 'flex', height: '100vh', width: '100vw', flexDirection: 'column' }}>
                <CssBaseline />
                <AppBar position="static" color="default" sx={{ boxShadow: 'none', borderBottom: 1, borderColor: 'divider' }}>
                    <Toolbar>
                        <Tooltip title="返回沙盒列表">
                             <IconButton color="inherit" onClick={handleGoBackToExplorer} edge="start" sx={{ mr: 2 }}>
                                <ArrowBackIcon />
                            </IconButton>
                        </Tooltip>
                        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
                            {sandboxName}
                        </Typography>
                    </Toolbar>
                </AppBar>

                <CockpitContent />
            </Box>
        </SandboxStateProvider>
    );
}

export default RunnerPage;