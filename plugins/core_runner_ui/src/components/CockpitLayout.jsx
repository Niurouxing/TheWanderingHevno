// plugins/core_runner_ui/src/components/CockpitLayout.jsx
import React, { useState, useMemo, useEffect } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
// --- 1. 导入 GlobalStyles ---
import { GlobalStyles } from '@mui/material';
import { useLayout } from '../../../core_layout/src/context/LayoutContext';
import { DynamicComponentLoader } from './DynamicComponentLoader';

import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

// --- 2. 定义我们的美化样式 ---
const placeholderStyles = `
  .react-grid-layout .react-grid-placeholder {
    background-color: rgba(0, 127, 255, 0.2); /* 一个更柔和的蓝色调，半透明 */
    border: 2px dashed rgba(0, 127, 255, 0.5); /* 虚线边框 */
    border-radius: 8px; /* 圆角，使其与你的UI更匹配 */
    transition: all 0.2s ease-in-out; /* 添加平滑的过渡效果 */
    opacity: 1 !important; /* 确保我们的样式生效 */
  }
`;

// [核心修改 1] 组件接收一个 'panels' prop
export function CockpitLayout({ panels = [] }) {
    const { services } = useLayout(); // 在这里获取 services
    // const contributionService = services.get('contributionService'); // 不再需要

    // [核心修改 2] availablePanels 直接使用传入的 prop
    const availablePanels = panels;

    const [activePanels] = useState(() => availablePanels.map(p => p.id));
    const [layouts, setLayouts] = useState({});

    useEffect(() => {
        const initialLayouts = {};
        availablePanels.forEach(p => {
            initialLayouts[p.id] = {
                ...(p.defaultLayout || { w: 4, h: 4, x: 0, y: 0 }),
                i: p.id,
            };
        });
        setLayouts({ lg: Object.values(initialLayouts) });
    }, [availablePanels]);

    const handleLayoutChange = (layout, allLayouts) => {
        setLayouts(allLayouts);
    };

    return (
        // --- 3. 使用 React.Fragment 包裹并应用 GlobalStyles ---
        <>
            <GlobalStyles styles={placeholderStyles} />
            <ResponsiveGridLayout
                // [核心修改 3] 确保 react-grid-layout 是透明的，这样才能看到下面的背景组件
                style={{ background: 'transparent' }}
                layouts={layouts}
                breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                rowHeight={30}
                onLayoutChange={handleLayoutChange}
                compactType={null} 
                draggableHandle=".drag-handle"
            >
                {activePanels.map(panelId => {
                    const panelInfo = availablePanels.find(p => p.id === panelId);
                    if (!panelInfo) return null;
                    
                    return (
                        <div key={panelId} style={{ background: 'transparent' }}>
                            {/* DynamicComponentLoader 现在需要从 services 容器获取 services */}
                            <DynamicComponentLoader contribution={panelInfo} services={services} />
                        </div>
                    );
                })}
            </ResponsiveGridLayout>
        </>
    );
}