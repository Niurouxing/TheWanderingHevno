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

export function CockpitLayout({ panels = [], activePanelIds = [], layouts = {}, onLayoutChange }) {
    const { services } = useLayout(); 
    
    return (
        <>
            <GlobalStyles styles={placeholderStyles} />
            <ResponsiveGridLayout
                style={{ background: 'transparent' }}
                layouts={layouts}
                breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                cols={{ lg: 24, md: 20, sm: 12, xs: 8, xxs: 4 }}
                rowHeight={30}
                onLayoutChange={onLayoutChange}
                // [核心修改] 禁用自动紧凑布局，这是允许自由定位的第一步。
                compactType={null}
                // [核心修改] 明确允许组件重叠。没有这个，拖动时组件依然会相互推挤。
                preventCollision={false}
                draggableHandle=".drag-handle"
            >
                {panels.map(panelInfo => {
                    const isActive = activePanelIds.includes(panelInfo.id);
                    
                    const style = {
                        background: 'transparent',
                        pointerEvents: isActive ? 'auto' : 'none',
                        visibility: isActive ? 'visible' : 'hidden',
                        // [新增] 当面板重叠时，确保被拖动的面板总是在最上层
                        zIndex: 100 // 可以根据需要调整
                    };

                    return (
                        <div key={panelInfo.id} style={style}>
                            <DynamicComponentLoader contribution={panelInfo} services={services} />
                        </div>
                    );
                })}
            </ResponsiveGridLayout>
        </>
    );
}