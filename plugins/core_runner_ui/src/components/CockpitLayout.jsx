// plugins/core_runner_ui/src/components/CockpitLayout.jsx
import React, { useState, useMemo } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { useLayout } from '../../../core_layout/src/context/LayoutContext';
import { Box, Paper, Typography, CircularProgress } from '@mui/material';

// 导入 react-grid-layout 的样式
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

// 【新增】创建一个样式组件来美化占位符
const GlobalStyles = () => {
    React.useEffect(() => {
        // 如果样式还没有注入，则注入全局样式
        if (!document.querySelector('#react-grid-layout-placeholder-styles')) {
            const style = document.createElement('style');
            style.id = 'react-grid-layout-placeholder-styles';
            style.textContent = `
                .react-grid-layout .react-grid-item.react-grid-placeholder {
                    background-color: rgba(0, 150, 255, 0.1) !important;
                    border: 2px dashed rgba(0, 150, 255, 0.5) !important;
                    border-radius: 8px !important;
                    transition: none !important;
                }
            `;
            document.head.appendChild(style);
        }
    }, []);
    
    return null;
};

const ResponsiveGridLayout = WidthProvider(Responsive);

// 动态组件缓存，防止重复创建 React.lazy 实例
const componentCache = new Map();

function getLazyPanelComponent(panelInfo) {
    if (componentCache.has(panelInfo.id)) {
        return componentCache.get(panelInfo.id);
    }
    const LazyComponent = React.lazy(async () => {
        const modulePath = `/plugins/${panelInfo.manifest.id}/${panelInfo.manifest.frontend.srcEntryPoint}`;
        try {
            const module = await import(/* @vite-ignore */ modulePath);
            if (module[panelInfo.componentExportName]) {
                return { default: module[panelInfo.componentExportName] };
            }
            throw new Error(`Component export '${panelInfo.componentExportName}' not found.`);
        } catch (error) {
            console.error(`Failed to load panel '${panelInfo.id}':`, error);
            const ErrorComponent = () => <Box sx={{ p: 1, color: 'error.main' }}>Error loading panel: {panelInfo.name}</Box>;
            return { default: ErrorComponent };
        }
    });
    componentCache.set(panelInfo.id, LazyComponent);
    return LazyComponent;
}

export function CockpitLayout() {
    const { services } = useLayout();
    const contributionService = services.get('contributionService');

    // 从贡献点发现所有可用的面板
    const availablePanels = useMemo(() =>
        contributionService.getContributionsFor('cockpit.panels'),
        [contributionService]
    );

    // TODO: 布局和激活的面板应从用户设置或 localStorage 加载
    // 目前，我们默认激活所有找到的面板
    const [activePanels] = useState(() => availablePanels.map(p => p.id));
    const [layouts, setLayouts] = useState(() => {
        const initialLayouts = {};
        availablePanels.forEach(p => {
            initialLayouts[p.id] = {
                ...(p.defaultLayout || { w: 4, h: 4, x: 0, y: 0 }),
                i: p.id,
            };
        });
        return { lg: Object.values(initialLayouts) };
    });

    const handleLayoutChange = (layout, allLayouts) => {
        // TODO: 将布局变化保存到 localStorage
        setLayouts(allLayouts);
    };

    const panelMap = useMemo(() =>
        new Map(availablePanels.map(p => [p.id, p])),
        [availablePanels]
    );

    return (
        <>
            {/* 【新增】将全局样式注入到组件中 */}
            <GlobalStyles />
            <ResponsiveGridLayout
                className="layout"
                layouts={layouts}
                breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                rowHeight={30}
                onLayoutChange={handleLayoutChange}
                draggableHandle=".drag-handle"
                compactType={null} 
            >
                {activePanels.map(panelId => {
                    const panelInfo = panelMap.get(panelId);
                    if (!panelInfo) return null;

                    const PanelComponent = getLazyPanelComponent(panelInfo);

                    return (
                        <Paper key={panelId} variant="outlined" sx={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                            <Box
                                className="drag-handle"
                                sx={{
                                    p: 1,
                                    cursor: 'move',
                                    bgcolor: 'rgba(255, 255, 255, 0.08)',
                                    borderBottom: 1,
                                    borderColor: 'divider',
                                    // 【修改】确保标题栏高度固定
                                    flexShrink: 0
                                }}
                            >
                                <Typography variant="subtitle2" noWrap>{panelInfo.name}</Typography>
                            </Box>
                            {/* 【修改】让这个Box占据所有剩余空间并可以内部滚动 */}
                            <Box sx={{ flex: '1 1 auto', overflowY: 'auto', p: 1 }}>
                                <React.Suspense fallback={<CircularProgress size={24} />}>
                                    <PanelComponent />
                                </React.Suspense>
                            </Box>
                        </Paper>
                    );
                })}
            </ResponsiveGridLayout>
        </>
    );
}