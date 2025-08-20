// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useMemo, useEffect, useState, useCallback } from 'react';
import { Box, Typography, CssBaseline, CircularProgress, Button } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { CockpitLayout } from './components/CockpitLayout';
import { DynamicComponentLoader } from './components/DynamicComponentLoader';
// --- 1. 导入新的 ManagementPanel ---
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
    
    // --- 2. 状态提升 ---
    // activePanelIds: 存储当前可见面板的ID列表
    // layouts: 存储 react-grid-layout 的布局信息
    const [activePanelIds, setActivePanelIds] = useState([]);
    const [layouts, setLayouts] = useState({});

    const getStorageKey = useCallback(() => `cockpit_layout_${sandboxId}`, [sandboxId]);

    // --- 3. 从 localStorage 加载或初始化布局 ---
    useEffect(() => {
        if (!sandboxId) return;

        const allAvailablePanels = contributionService.getContributionsFor('cockpit.panels');
        const storageKey = getStorageKey();
        let savedState = null;
        try {
            const savedJson = localStorage.getItem(storageKey);
            if (savedJson) {
                savedState = JSON.parse(savedJson);
            }
        } catch (e) {
            console.error("Failed to parse cockpit layout from localStorage", e);
            localStorage.removeItem(storageKey);
        }

        if (savedState && savedState.activePanelIds && savedState.layouts) {
            // 健壮性检查: 只加载仍然存在的插件面板
            const existingPanelIds = savedState.activePanelIds.filter(id => 
                allAvailablePanels.some(p => p.id === id)
            );
            setActivePanelIds(existingPanelIds);
            setLayouts(savedState.layouts);
        } else {
            // 如果没有保存的状态，则初始化默认布局
            const defaultActivePanels = allAvailablePanels.filter(p => p.defaultEnabled);
            const initialLayouts = {};
            const layoutForBreakpoint = defaultActivePanels.map(p => ({
                ...(p.defaultLayout || { w: 4, h: 4, x: 0, y: 0 }),
                i: p.id,
            }));

            // react-grid-layout 需要为每个断点设置布局
            initialLayouts['lg'] = layoutForBreakpoint;
            
            setActivePanelIds(defaultActivePanels.map(p => p.id));
            setLayouts(initialLayouts);
        }
    }, [sandboxId, contributionService, getStorageKey]);

    // --- 4. 将布局变化持久化到 localStorage ---
    useEffect(() => {
        // 避免在初始加载时写入空的 state
        if (!sandboxId || activePanelIds.length === 0) return;

        try {
            const stateToSave = { activePanelIds, layouts };
            localStorage.setItem(getStorageKey(), JSON.stringify(stateToSave));
        } catch (e) {
            console.error("Failed to save cockpit layout to localStorage", e);
        }
    }, [activePanelIds, layouts, sandboxId, getStorageKey]);
    
    // --- 5. 管理面板的逻辑函数 ---
    const handleTogglePanel = (panelId) => {
        setActivePanelIds(prev => {
            if (prev.includes(panelId)) {
                return prev.filter(id => id !== panelId);
            } else {
                return [...prev, panelId];
            }
        });
    };

    const handleResetLayout = () => {
        if (window.confirm('你确定要重置驾驶舱布局到默认设置吗？')) {
            localStorage.removeItem(getStorageKey());
            window.location.reload(); // 最简单的重置方式
        }
    };


    const { backgroundComponent, panelComponents } = useMemo(() => {
        const backgroundContributions = contributionService.getContributionsFor('cockpit.canvas_background');
        const panelContributions = contributionService.getContributionsFor('cockpit.panels');
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
            
            <Box sx={{ flexGrow: 1, position: 'relative', overflow: 'hidden' }}>
                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }}>
                    {backgroundComponent ? (
                        <DynamicComponentLoader 
                            contribution={backgroundComponent} 
                            services={stableServices}
                            props={{ moment, performStep, isStepping, sandboxId }}
                        />
                    ) : (
                        <Box sx={{ width: '100%', height: '100%', bgcolor: 'background.default' }} />
                    )}
                </Box>

                <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2, overflow: 'auto', pointerEvents: 'none' }}>
                    {/* --- 6. 将状态和回调传递给 CockpitLayout --- */}
                    <CockpitLayout 
                        panels={panelComponents} 
                        activePanelIds={activePanelIds}
                        layouts={layouts}
                        onLayoutChange={setLayouts}
                    />
                </Box>
                
                {/* --- 7. 渲染 ManagementPanel --- */}
                <ManagementPanel
                    isOpen={isManaging}
                    onClose={() => setIsManaging(false)}
                    availablePanels={panelComponents}
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