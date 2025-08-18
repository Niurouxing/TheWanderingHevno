// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useMemo } from 'react';
import { Box, Typography, CssBaseline, CircularProgress } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { CockpitLayout } from './components/CockpitLayout';
import { DynamicComponentLoader } from './components/DynamicComponentLoader';

// CockpitContent 现在负责渲染所有动态加载的UI部分
function CockpitContent() {
    const { services } = useLayout();
    const { isLoading, moment } = useSandboxState();
    const contributionService = services.get('contributionService');

    // 查找 "chrome" (镶边) UI 组件
    const chromeComponents = useMemo(() => {
        const contributions = contributionService.getContributionsFor('cockpit.chrome');
        const topBar = contributions.find(c => c.slot === 'top-bar');
        const bottomBar = contributions.find(c => c.slot === 'bottom-bar');
        return { topBar, bottomBar };
    }, [contributionService]);

    if (isLoading && !moment) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {chromeComponents.topBar && (
                <Box sx={{ flexShrink: 0 }}>
                    <DynamicComponentLoader contribution={chromeComponents.topBar} />
                </Box>
            )}

            <Box sx={{ flexGrow: 1, position: 'relative' /* 确保网格布局正常工作 */ }}>
                <CockpitLayout />
            </Box>

            {chromeComponents.bottomBar && (
                <Box sx={{ flexShrink: 0, p: { xs: 1, sm: 2 } }}>
                    <DynamicComponentLoader contribution={chromeComponents.bottomBar} />
                </Box>
            )}
        </Box>
    );
}

export function RunnerPage() {
    const { currentSandboxId } = useLayout();

    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h5">开始交互</Typography>
                <Typography color="text.secondary">请从 "沙盒列表" 页面选择一个沙盒以开始。</Typography>
            </Box>
        );
    }

    return (
        // SandboxStateProvider 现在包裹整个页面，为所有动态组件提供数据
        <SandboxStateProvider sandboxId={currentSandboxId}>
            <CssBaseline />
            <CockpitContent />
        </SandboxStateProvider>
    );
}

export default RunnerPage;