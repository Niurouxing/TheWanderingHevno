// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useMemo, useEffect, useState } from 'react'; // [修改] 导入 useEffect 和 useState
import { Box, Typography, CssBaseline, CircularProgress } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { CockpitLayout } from './components/CockpitLayout';
import { DynamicComponentLoader } from './components/DynamicComponentLoader';

// [新] 导入我们将用于自定义按钮的图标
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import TuneIcon from '@mui/icons-material/Tune';


// CockpitContent 现在负责渲染所有动态加载的UI部分
function CockpitContent() {
    const { services, setActivePageId, setMenuOverride } = useLayout(); // [修改] 获取 setMenuOverride
    const { isLoading, moment } = useSandboxState();
    const contributionService = services.get('contributionService');
    
    // [新] 添加一个状态来控制管理面板的显示
    const [isManaging, setIsManaging] = useState(false);

    // --- [新] 核心逻辑：使用 useEffect 在组件挂载时设置菜单重写，在卸载时清除它 ---
    useEffect(() => {
        // 定义自定义操作
        const runnerMenuActions = [
            {
                id: 'runner.back',
                title: '返回沙盒列表',
                icon: <ArrowBackIcon />,
                onClick: () => setActivePageId('sandbox_explorer.main_view'),
            },
            {
                id: 'runner.manage',
                title: '管理驾驶舱',
                icon: <TuneIcon />,
                onClick: () => {
                    setIsManaging(prev => !prev);
                    console.log('Toggling Cockpit Management UI...');
                },
                // 如果管理面板打开，让按钮高亮
                isActive: isManaging, 
            }
        ];

        // 设置重写
        setMenuOverride(runnerMenuActions);

        // 清理函数：当组件卸载时，移除重写
        return () => {
            setMenuOverride(null);
        };
    // [修改] 依赖项确保此 effect 仅在关键函数变化时重新运行
    }, [setMenuOverride, setActivePageId, isManaging]);


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
                {isManaging && (
                    <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, bgcolor: 'rgba(0,0,0,0.7)', zIndex: 10, p: 2, color: 'white' }}>
                        <Typography variant="h6">驾驶舱管理面板</Typography>
                        <Typography>这里可以放置用于显示/隐藏/重新排列 Cockpit 面板的控件。</Typography>
                        <Button onClick={() => setIsManaging(false)} variant="contained" sx={{mt: 2}}>关闭</Button>
                    </Box>
                )}
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