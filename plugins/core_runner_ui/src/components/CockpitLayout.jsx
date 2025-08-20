// plugins/core_runner_ui/src/components/CockpitLayout.jsx
import React from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import { GlobalStyles } from '@mui/material';
import { useLayout } from '../../../core_layout/src/context/LayoutContext';
import { DynamicComponentLoader } from './DynamicComponentLoader';

import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

const placeholderStyles = `
  .react-grid-layout .react-grid-placeholder {
    background-color: rgba(0, 127, 255, 0.2);
    border: 2px dashed rgba(0, 127, 255, 0.5);
    border-radius: 8px;
    transition: all 0.2s ease-in-out;
    opacity: 1 !important;
  }
`;

// [核心修改] 组件现在是无状态的，接收所有必要的 props
export function CockpitLayout({ panels = [], activePanelIds = [], layouts = {}, onLayoutChange }) {
    const { services } = useLayout(); 
    
    // 从所有可用面板中，只渲染那些ID在 activePanelIds 列表中的面板
    const panelsToRender = panels.filter(p => activePanelIds.includes(p.id));

    return (
        <>
            <GlobalStyles styles={placeholderStyles} />
            <ResponsiveGridLayout
                style={{ background: 'transparent' }}
                layouts={layouts}
                breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                cols={{ lg: 24, md: 20, sm: 12, xs: 8, xxs: 4 }}
                rowHeight={30}
                onLayoutChange={(layout, allLayouts) => onLayoutChange(allLayouts)} // 将事件冒泡上去
                compactType={null} 
                draggableHandle=".drag-handle"
            >
                {panelsToRender.map(panelInfo => (
                    <div key={panelInfo.id} style={{ background: 'transparent', pointerEvents: 'auto' }}>
                        <DynamicComponentLoader contribution={panelInfo} services={services} />
                    </div>
                ))}
            </ResponsiveGridLayout>
        </>
    );
}