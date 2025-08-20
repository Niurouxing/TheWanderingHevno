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
    // [改动] 从 useSandboxState 获取所有需要传递给子组件的值
    const { isLoading, moment, performStep, isStepping } = useSandboxState();
    
    // [核心修复 2] 稳定 services 对象，防止不必要的重渲染
    const stableServices = useMemo(() => services, [services]);
    
    const contributionService = stableServices.get('contributionService');
    const hookManager = stableServices.get('hookManager');

    const [isManaging, setIsManaging] = useState(false);

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
            {chromeComponents.topBar && <Box sx={{ flexShrink: 0 }}><DynamicComponentLoader contribution={chromeComponents.topBar} services={stableServices} /></Box>}
            
            <Box sx={{ flexGrow: 1, position: 'relative',overflow: 'hidden'  }}>
                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }}>
                    {backgroundComponent ? (
                        // [改动] 将状态和函数作为 props 注入到动态加载的组件中
                        <DynamicComponentLoader 
                            contribution={backgroundComponent} 
                            services={stableServices}
                            props={{ moment, performStep, isStepping }}
                        />
                    ) : (
                        // 如果没有背景组件，可以提供一个默认的、简单的背景
                        <Box sx={{ width: '100%', height: '100%', bgcolor: 'background.default' }} />
                    )}
                </Box>

                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2,overflow: 'auto' ,pointerEvents: 'none' }}>
                    {/* 我们将 panelComponents 传递给 CockpitLayout */}
                    <CockpitLayout panels={panelComponents} />
                </Box>

                {isManaging && (
                    <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, bgcolor: 'rgba(0,0,0,0.7)', zIndex: 10, p: 2, color: 'white' }}>
                        <Typography variant="h6">驾驶舱管理面板</Typography>
                        <Button onClick={() => setIsManaging(false)} variant="contained" sx={{mt: 2}}>关闭</Button>
                    </Box>
                )}

            </Box>
            
            {chromeComponents.bottomBar && <Box sx={{ flexShrink: 0 }}><DynamicComponentLoader contribution={chromeComponents.bottomBar} services={stableServices} /></Box>}
        </Box>
    );
}

export function RunnerPage() {
    const { currentSandboxId, services } = useLayout();
    
    // [核心修复 3] 同样在这里稳定 services 对象
    const stableServices = useMemo(() => services, [services]);
    
    if (!currentSandboxId) {
        return (
            <Box sx={{ p: 4, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h5">开始交互</Typography>
                <Typography color="text.secondary">请从 "沙盒列表" 页面选择一个沙盒以开始。</Typography>
            </Box>
        );
    }
    return (
        <SandboxStateProvider sandboxId={currentSandboxId} services={stableServices}>
            <CssBaseline />
            <CockpitContent />
        </SandboxStateProvider>
    );
}

export default RunnerPage;