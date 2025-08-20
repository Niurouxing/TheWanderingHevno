// plugins/core_runner_ui/src/RunnerPage.jsx
import React, { useMemo, useEffect, useState, useCallback } from 'react';
import { Box, Typography, CssBaseline, CircularProgress } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext';
import { SandboxStateProvider, useSandboxState } from './context/SandboxStateContext';
import { DynamicComponentLoader } from './components/DynamicComponentLoader';
import { ManagementPanel } from './components/ManagementPanel';
import { ChromeActionsBar } from './components/ChromeActionsBar';
import { FloatingPanel } from './components/FloatingPanel'; // 保持不变

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import TuneIcon from '@mui/icons-material/Tune';
import * as MuiIcons from '@mui/icons-material';

const DynamicIcon = ({ name }) => {
  if (React.isValidElement(name)) return name;
  const Icon = MuiIcons[name];
  return Icon ? <Icon /> : null;
};

const BASE_Z_INDEX = 100;

function CockpitContent() {
    const { services, setActivePageId, setMenuOverride } = useLayout();
    const { sandboxId, isLoading, moment, performStep, isStepping } = useSandboxState();
    const stableServices = useMemo(() => services, [services]);
    const contributionService = stableServices.get('contributionService');
    const hookManager = stableServices.get('hookManager');

    const [isManaging, setIsManaging] = useState(false);
    const [activeBackgroundId, setActiveBackgroundId] = useState(null);

    const [panelStates, setPanelStates] = useState({});
    const [highestZIndex, setHighestZIndex] = useState(BASE_Z_INDEX);

    const getStorageKey = useCallback(() => `cockpit_freelayout_v1_${sandboxId}`, [sandboxId]);

    const { availableBackgrounds, availablePanels } = useMemo(() => {
        const backgrounds = contributionService.getContributionsFor('cockpit.canvas_background');
        const panels = contributionService.getContributionsFor('cockpit.panels');
        return { availableBackgrounds: backgrounds, availablePanels: panels };
    }, [contributionService]);

    useEffect(() => {
        if (!sandboxId) return;
        
        let savedState = null;
        try {
            const savedJson = localStorage.getItem(getStorageKey());
            if (savedJson) savedState = JSON.parse(savedJson);
        } catch (e) {
            console.error("Failed to parse cockpit layout from localStorage", e);
            localStorage.removeItem(getStorageKey());
        }

        const initialStates = {};
        let maxZ = BASE_Z_INDEX;

        availablePanels.forEach((panel, index) => {
            const savedPanelState = savedState?.panelStates?.[panel.id];
            const defaultState = panel.defaultState || { x: 50 + index * 20, y: 50 + index * 20, width: 450, height: 400 };
            
            initialStates[panel.id] = {
                x: savedPanelState?.x ?? defaultState.x,
                y: savedPanelState?.y ?? defaultState.y,
                width: savedPanelState?.width ?? defaultState.width,
                height: savedPanelState?.height ?? defaultState.height,
                zIndex: savedPanelState?.zIndex ?? (BASE_Z_INDEX + index),
                isVisible: savedPanelState?.isVisible ?? panel.defaultEnabled,
            };
            
            if (initialStates[panel.id].zIndex > maxZ) {
                maxZ = initialStates[panel.id].zIndex;
            }
        });

        setPanelStates(initialStates);
        setHighestZIndex(maxZ);
        const defaultBg = availableBackgrounds.find(bg => bg.defaultEnabled);
        setActiveBackgroundId(savedState?.activeBackgroundId ?? (defaultBg ? defaultBg.id : null));

    }, [sandboxId, availablePanels, availableBackgrounds, getStorageKey]);

    useEffect(() => {
        if (!sandboxId || Object.keys(panelStates).length === 0) return;
        
        const stateToSave = {
            activeBackgroundId,
            panelStates
        };
        localStorage.setItem(getStorageKey(), JSON.stringify(stateToSave));

    }, [activeBackgroundId, panelStates, sandboxId, getStorageKey]);
    
    const handlePanelFocus = useCallback((panelId) => {
        const newZ = highestZIndex + 1;
        setHighestZIndex(newZ);
        setPanelStates(prev => ({
            ...prev,
            [panelId]: { ...prev[panelId], zIndex: newZ }
        }));
    }, [highestZIndex]);
    
    const handlePanelDragStop = useCallback((panelId, position) => {
        setPanelStates(prev => ({
            ...prev,
            [panelId]: { ...prev[panelId], x: position.x, y: position.y }
        }));
    }, []);

    // --- [新增] 创建一个新的回调函数来处理缩放停止事件 ---
    const handlePanelResizeStop = useCallback((panelId, size) => {
        setPanelStates(prev => ({
            ...prev,
            [panelId]: { ...prev[panelId], width: size.width, height: size.height }
        }));
    }, []);


    const handleTogglePanel = (panelId) => {
        setPanelStates(prev => {
            const isVisible = !prev[panelId].isVisible;
            const newZ = isVisible ? highestZIndex + 1 : prev[panelId].zIndex;
            if (isVisible) setHighestZIndex(newZ);

            return {
                ...prev,
                [panelId]: { ...prev[panelId], isVisible, zIndex: newZ }
            };
        });
    };

    const handleResetLayout = () => {
        if (window.confirm('你确定要重置驾驶舱布局到默认设置吗？')) {
            localStorage.removeItem(getStorageKey());
            window.location.reload();
        }
    };
    
    const backgroundToRender = useMemo(() => {
        if (!activeBackgroundId) return null;
        return availableBackgrounds.find(bg => bg.id === activeBackgroundId);
    }, [activeBackgroundId, availableBackgrounds]);

    const activePanelIds = useMemo(() => 
        Object.entries(panelStates)
            .filter(([, state]) => state.isVisible)
            .map(([id]) => id),
        [panelStates]
    );

    // ... (runnerMenuActions, chromeActions, chromeComponents 的 useMemo 钩子保持不变) ...
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
                onClick: () => hookManager?.trigger(contrib.hookName)
            }));
        return [...baseActions, ...contributedActions];
    }, [contributionService, hookManager, setActivePageId, isManaging]);

    useEffect(() => {
        setMenuOverride(runnerMenuActions);
        return () => setMenuOverride(null);
    }, [setMenuOverride, runnerMenuActions]);

    const chromeActions = useMemo(() => {
        return contributionService.getContributionsFor('cockpit.chrome_actions');
    }, [contributionService]);

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
                
                {availablePanels.map(panelInfo => {
                    const state = panelStates[panelInfo.id];
                    if (!state || !state.isVisible) return null;
                    
                    return (
                        <FloatingPanel
                            key={panelInfo.id}
                            panelId={panelInfo.id}
                            panelState={state}
                            onFocus={handlePanelFocus}
                            onDragStop={handlePanelDragStop}
                            onResizeStop={handlePanelResizeStop} // <-- 将新的回调函数传递下去
                        >
                            <DynamicComponentLoader contribution={panelInfo} services={stableServices} />
                        </FloatingPanel>
                    );
                })}
                
                <ChromeActionsBar
                    actions={chromeActions}
                    activePanelIds={activePanelIds}
                    onTogglePanel={handleTogglePanel}
                />
                
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

// RunnerPage 组件本身不需要修改
export function RunnerPage() {
    const { currentSandboxId, services } = useLayout();
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