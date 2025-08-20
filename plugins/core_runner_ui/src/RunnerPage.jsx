// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useMemo, useEffect, useState, useCallback } from 'react';
import { Box, Typography, CssBaseline, CircularProgress } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { CockpitLayout } from './components/CockpitLayout';
import { DynamicComponentLoader } from './components/DynamicComponentLoader';
import { ManagementPanel } from './components/ManagementPanel';

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
    const { sandboxId, isLoading, moment, performStep, isStepping } = useSandboxState();
    const stableServices = useMemo(() => services, [services]);
    const contributionService = stableServices.get('contributionService');
    const hookManager = stableServices.get('hookManager');

    const [isManaging, setIsManaging] = useState(false);
    
    // [核心修改] 状态现在区分为 activeBackgroundId 和 activePanelIds
    const [activeBackgroundId, setActiveBackgroundId] = useState(null);
    const [activePanelIds, setActivePanelIds] = useState([]);
    const [layouts, setLayouts] = useState({});

    const getStorageKey = useCallback(() => `cockpit_layout_v2_${sandboxId}`, [sandboxId]);

    // [核心修改] 将所有可用的背景和面板组件 memoize
    const { availableBackgrounds, availablePanels } = useMemo(() => {
        const backgrounds = contributionService.getContributionsFor('cockpit.canvas_background');
        const panels = contributionService.getContributionsFor('cockpit.panels');
        return { availableBackgrounds: backgrounds, availablePanels: panels };
    }, [contributionService]);

    // 从 localStorage 加载或初始化布局
    useEffect(() => {
        if (!sandboxId) return;

        const storageKey = getStorageKey();
        let savedState = null;
        try {
            const savedJson = localStorage.getItem(storageKey);
            if (savedJson) savedState = JSON.parse(savedJson);
        } catch (e) {
            console.error("Failed to parse cockpit layout from localStorage", e);
            localStorage.removeItem(storageKey);
        }

        if (savedState) {
            // 加载已保存的状态
            setActiveBackgroundId(savedState.activeBackgroundId || null);
            
            const existingPanelIds = savedState.activePanelIds?.filter(id => 
                availablePanels.some(p => p.id === id)
            ) || [];
            setActivePanelIds(existingPanelIds);
            
            setLayouts(savedState.layouts || {});

        } else {
            // 初始化默认状态
            const defaultBg = availableBackgrounds.find(bg => bg.defaultEnabled);
            setActiveBackgroundId(defaultBg ? defaultBg.id : null);

            const defaultPanels = availablePanels.filter(p => p.defaultEnabled);
            setActivePanelIds(defaultPanels.map(p => p.id));
            
            // [解决尺寸丢失的关键] 为 *所有* 可用面板创建初始布局，而不仅仅是激活的
            const initialLayouts = {};
            const allPanelsLayout = availablePanels.map(p => ({
                ...(p.defaultLayout || { w: 6, h: 8, x: 0, y: Infinity }), // y: Infinity让r-g-l自动堆叠
                i: p.id,
            }));
            initialLayouts['lg'] = allPanelsLayout;
            setLayouts(initialLayouts);
        }
    }, [sandboxId, availableBackgrounds, availablePanels, getStorageKey]);

    // 将布局变化持久化到 localStorage
    useEffect(() => {
        if (!sandboxId) return;
        // 避免在初始加载时写入不完整的 state
        if (Object.keys(layouts).length === 0 && activePanelIds.length === 0 && !activeBackgroundId) return;

        try {
            const stateToSave = { activeBackgroundId, activePanelIds, layouts };
            localStorage.setItem(getStorageKey(), JSON.stringify(stateToSave));
        } catch (e) {
            console.error("Failed to save cockpit layout to localStorage", e);
        }
    }, [activeBackgroundId, activePanelIds, layouts, sandboxId, getStorageKey]);
    
    // [解决尺寸丢失的关键] 新的布局变化处理器
    // 它将 react-grid-layout 返回的局部布局信息合并到我们完整的布局状态中
    const handleLayoutChange = (newLayout, allLayouts) => {
        setLayouts(prev => ({ ...prev, ...allLayouts }));
    };

    const handleTogglePanel = (panelId) => {
        setActivePanelIds(prev =>
            prev.includes(panelId)
                ? prev.filter(id => id !== panelId)
                : [...prev, panelId]
        );
    };

    const handleResetLayout = () => {
        if (window.confirm('你确定要重置驾驶舱布局到默认设置吗？')) {
            localStorage.removeItem(getStorageKey());
            window.location.reload();
        }
    };
    
    // [核心修改] 动态查找要渲染的背景组件
    const backgroundToRender = useMemo(() => {
        if (!activeBackgroundId) return null;
        return availableBackgrounds.find(bg => bg.id === activeBackgroundId);
    }, [activeBackgroundId, availableBackgrounds]);


    const runnerMenuActions = useMemo(() => {
        const baseActions = [
            { id: 'runner.back', title: '返回沙盒列表', icon: <ArrowBackIcon />, onClick: () => setActivePageId('sandbox_explorer.main_view') },
            { id: 'runner.manage', title: '管理驾驶舱', icon: <TuneIcon />, onClick: () => setIsManaging(prev => !prev), isActive: isManaging }
        ];
        // ... (contributedActions logic remains the same)
        const contributedActions = contributionService.getContributionsFor('core_runner_ui.menu_actions')
            .map(contrib => ({
                id: contrib.id,
                title: contrib.title,
                icon: <DynamicIcon name={contrib.icon} />,
                onClick: () => hookManager?.trigger(contrib.hookName)
            }));
        return [...baseActions, ...contributedActions];
    }, [contributionService, hookManager, setActivePageId, isManaging]);

    useEffect(() => {
        setMenuOverride(runnerMenuActions);
        return () => setMenuOverride(null);
    }, [setMenuOverride, runnerMenuActions]);

    const chromeComponents = useMemo(() => {
        // ... (this logic remains the same)
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
            
            <Box sx={{ flexGrow: 1, position: 'relative', overflow: 'hidden' }}>
                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }}>
                    {backgroundToRender ? (
                        <DynamicComponentLoader 
                            contribution={backgroundToRender} 
                            services={stableServices}
                            props={{ moment, performStep, isStepping, sandboxId }}
                        />
                    ) : (
                        <Box sx={{ width: '100%', height: '100%', bgcolor: '#22272B' }} />
                    )}
                </Box>

                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2, overflow: 'auto', pointerEvents: 'none' }}>
                    <CockpitLayout 
                        panels={availablePanels} 
                        activePanelIds={activePanelIds}
                        layouts={layouts}
                        onLayoutChange={handleLayoutChange}
                    />
                </Box>
                
                <ManagementPanel
                    isOpen={isManaging}
                    onClose={() => setIsManaging(false)}
                    availableBackgrounds={availableBackgrounds}
                    activeBackgroundId={activeBackgroundId}
                    onSelectBackground={setActiveBackgroundId}
                    availablePanels={availablePanels}
                    activePanelIds={activePanelIds}
                    onTogglePanel={handleTogglePanel}
                    onResetLayout={handleResetLayout}
                />
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