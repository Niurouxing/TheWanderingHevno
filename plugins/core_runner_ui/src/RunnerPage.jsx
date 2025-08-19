// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useMemo, useEffect, useState } from 'react';
import { Box, Typography, CssBaseline, CircularProgress, Button } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { CockpitLayout } from './components/CockpitLayout';
import { DynamicComponentLoader } from './components/DynamicComponentLoader';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import TuneIcon from '@mui/icons-material/Tune';
import * as MuiIcons from '@mui/icons-material';

const DynamicIcon = ({ name }) => {
  if (React.isValidElement(name)) return name;
  const Icon = MuiIcons[name];
  return Icon ? <Icon /> : null;
};

function CockpitContent() {
    const { services, setActivePageId, setMenuOverride } = useLayout();
    const { isLoading, moment } = useSandboxState();
    const contributionService = services.get('contributionService');
    const hookManager = services.get('hookManager');

    const [isManaging, setIsManaging] = useState(false);

    // [核心修改 1] 使用 useMemo 分别获取两种类型的贡献
    const { backgroundComponent, panelComponents } = useMemo(() => {
        const backgroundContributions = contributionService.getContributionsFor('cockpit.canvas_background');
        const panelContributions = contributionService.getContributionsFor('cockpit.panels');

        // 正常情况下，背景组件只有一个。我们取第一个。
        const background = backgroundContributions.length > 0 ? backgroundContributions[0] : null;
        
        return {
            backgroundComponent: background,
            panelComponents: panelContributions
        };
    }, [contributionService]);

    // [最终形态] 动态构建菜单
    const runnerMenuActions = useMemo(() => {
        const baseActions = [
            { id: 'runner.back', title: '返回沙盒列表', icon: <ArrowBackIcon />, onClick: () => setActivePageId('sandbox_explorer.main_view') },
            { id: 'runner.manage', title: '管理驾驶舱', icon: <TuneIcon />, onClick: () => setIsManaging(prev => !prev), isActive: isManaging }
        ];
        const contributedActions = contributionService.getContributionsFor('core_runner_ui.menu_actions')
            .map(contrib => ({
                id: contrib.id,
                title: contrib.title,
                icon: <DynamicIcon name={contrib.icon} />,
                onClick: () => {
                    if (hookManager && contrib.hookName) {
                        hookManager.trigger(contrib.hookName);
                    }
                }
            }));
        return [...baseActions, ...contributedActions];
    }, [contributionService, hookManager, setActivePageId, isManaging]);

    useEffect(() => {
        setMenuOverride(runnerMenuActions);
        return () => setMenuOverride(null);
    }, [setMenuOverride, runnerMenuActions]);

    const chromeComponents = useMemo(() => {
        const contributions = contributionService.getContributionsFor('cockpit.chrome');
        return {
            topBar: contributions.find(c => c.slot === 'top-bar'),
            bottomBar: contributions.find(c => c.slot === 'bottom-bar'),
        };
    }, [contributionService]);

    if (isLoading && !moment) {
        return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {chromeComponents.topBar && <Box sx={{ flexShrink: 0 }}><DynamicComponentLoader contribution={chromeComponents.topBar} services={services} /></Box>}
            
            {/* [核心修改 2] 创建一个外层容器来容纳分层 */}
            {/* 这个 Box 是新的，用于确保背景和前景都相对于它进行定位 */}
            <Box sx={{ flexGrow: 1, position: 'relative' }}>

                {/* --- 背景层 --- */}
                {/* [核心修改 3] 渲染背景组件 */}
                {/* 它会绝对定位于外层容器，并铺满 */}
                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }}>
                    {backgroundComponent ? (
                        <DynamicComponentLoader contribution={backgroundComponent} services={services} />
                    ) : (
                        // 如果没有背景组件，可以提供一个默认的、简单的背景
                        <Box sx={{ width: '100%', height: '100%', bgcolor: 'background.default' }} />
                    )}
                </Box>

                {/* --- 前景层 --- */}
                {/* [核心修改 4] 渲染可拖拽面板的布局容器 */}
                {/* 它也绝对定位于外层容器，并浮动在背景之上 */}
                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2 }}>
                    {/* 我们将 panelComponents 传递给 CockpitLayout */}
                    <CockpitLayout panels={panelComponents} />
                </Box>

                {/* 管理模式的遮罩层，需要最高的 z-index */}
                {isManaging && (
                    <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, bgcolor: 'rgba(0,0,0,0.7)', zIndex: 10, p: 2, color: 'white' }}>
                        <Typography variant="h6">驾驶舱管理面板</Typography>
                        <Button onClick={() => setIsManaging(false)} variant="contained" sx={{mt: 2}}>关闭</Button>
                    </Box>
                )}

            </Box>
            
            {chromeComponents.bottomBar && <Box sx={{ flexShrink: 0 }}><DynamicComponentLoader contribution={chromeComponents.bottomBar} services={services} /></Box>}
        </Box>
    );
}

export function RunnerPage() {
    const { currentSandboxId, services } = useLayout();
    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h5">开始交互</Typography>
                <Typography color="text.secondary">请从 "沙盒列表" 页面选择一个沙盒以开始。</Typography>
            </Box>
        );
    }
    return (
        <SandboxStateProvider sandboxId={currentSandboxId} services={services}>
            <CssBaseline />
            <CockpitContent />
        </SandboxStateProvider>
    );
}

export default RunnerPage;