// plugins/core_runner_ui/src/components/FloatingPanel.jsx
import React, { useState, useEffect, useRef, Suspense } from 'react';
import Draggable from 'react-draggable';
import { ResizableBox } from 'react-resizable';
import { Box, Paper, CircularProgress } from '@mui/material';

import 'react-resizable/css/styles.css';



/**
 * @description 一个可配置的、用于绘制边角拖拽手柄的 SVG 图标。
 * @param {object} props
 * @param {number} props.size - 图标的整体尺寸 (宽度和高度)。
 * @param {number} props.cornerRadius - 圆角的半径。
 * @param {number} props.strokeWidth - 线条的粗细。
 */
const CornerHandleIcon = ({ size, cornerRadius, strokeWidth, ...rest }) => {
  // 计算直线的长度
  const lineLength = size - cornerRadius;

  // 动态生成 SVG path 的 'd' 属性
  // M = MoveTo: 移动到起点 (左下角)
  // L = LineTo: 画一条直线到圆角开始处
  // A = ArcTo: 画一个圆弧 (rx, ry, rotation, large-arc-flag, sweep-flag, x, y)
  // L = LineTo: 从圆角结束处画一条垂直线到终点
  const pathData = `
    M 0 ${size}
    L ${lineLength} ${size}
    A ${cornerRadius} ${cornerRadius} 0 0 0 ${size} ${lineLength}
    L ${size} 0
  `;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...rest}
    >
      <path
        d={pathData}
        strokeWidth={strokeWidth}
        strokeLinecap="round" // 让线条末端也是圆角，更柔和
        strokeLinejoin="round" // 让线条连接处也是圆角
      />
    </svg>
  );
};


/**
 * @description 自定义的拖拽手柄，现在支持自定义图标和偏移量。
 */
const CustomResizeHandle = React.forwardRef((props, ref) => {
  const { handleAxis, ...restProps } = props;

  // --- 在这里配置你的 Handle 图标 ---
  const iconSize = 10;      // 图标的总尺寸
  const cornerRadius = 8;     // 圆角的半径
  const strokeWidth = 2;      // 线条的粗细
  const offsetX = 7;        // 右侧偏移量 (正值向内)
  const offsetY = 3;        // 底部偏移量 (正值向内)
  // ------------------------------------

  return (
    <Box
      ref={ref}
      {...restProps}
      sx={{
        // Handle 的可点击区域，覆盖右下角
        position: 'absolute',
        width: 24, // 可以比图标稍大，增加点击区域
        height: 24,
        bottom: 0,
        right: 0,
        cursor: 'se-resize',
        
        // 使用 flexbox 精准控制内部图标的位置
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'flex-end',
      }}
    >
      <Box
        sx={{
          // 这个内部 Box 专门用来应用偏移量
          position: 'relative',
          right: `${offsetX}px`,
          bottom: `${offsetY}px`,

          // 设置 SVG 颜色和悬停效果
          '& svg': {
            stroke: 'rgba(255, 255, 255, 0.5)',
            transition: 'stroke 0.2s ease',
          },
          '&:hover svg': {
            stroke: 'rgba(255, 255, 255, 0.9)',
          },
        }}
      >
        <CornerHandleIcon
          size={iconSize}
          cornerRadius={cornerRadius}
          strokeWidth={strokeWidth}
        />
      </Box>
    </Box>
  );
});

// 将 DynamicComponentLoader 中的懒加载逻辑移到这里
const componentCache = new Map();
function getLazyComponent(contribution) {
    const cacheKey = `${contribution.pluginId}-${contribution.componentExportName}`;
    if (componentCache.has(cacheKey)) {
        return componentCache.get(cacheKey);
    }

    const LazyComponent = React.lazy(async () => {
        // 在 DEV 模式下，优先使用 srcEntryPoint 以支持热重载
        const entryPoint = import.meta.env.DEV 
            ? contribution.manifest.frontend.srcEntryPoint
            : contribution.manifest.frontend.entryPoint;

        const modulePath = `/plugins/${contribution.pluginId}/${entryPoint}`;
        try {
            const module = await import(/* @vite-ignore */ modulePath);
            if (module[contribution.componentExportName]) {
                return { default: module[contribution.componentExportName] };
            }
            throw new Error(`Component export '${contribution.componentExportName}' not found in plugin '${contribution.pluginId}'.`);
        } catch (error) {
            console.error(error);
            const ErrorComponent = () => <Box sx={{ p: 1, color: 'error.main' }}>Error loading component: {contribution.id}</Box>;
            return { default: ErrorComponent };
        }
    });

    componentCache.set(cacheKey, LazyComponent);
    return LazyComponent;
}

// 一个用于 Suspense fallback 的占位符组件
const LoadingPlaceholder = ({ width, height }) => (
    <Paper 
        sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            // 沿用 SnapshotHistoryPanel 的毛玻璃风格作为加载背景
            backgroundColor: 'rgba(40, 40, 40, 0.35)',
            backdropFilter: 'blur(15px) saturate(200%)',
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        }}
    >
        <CircularProgress />
    </Paper>
);

export function FloatingPanel({
  panelId,
  panelState,
  onDragStop,
  onResizeStop,
  onFocus,
  contribution,
  services
}) {
  const nodeRef = useRef(null);
  
  // 内部尺寸状态保持不变
  const [size, setSize] = useState({ width: panelState.width, height: panelState.height });

  useEffect(() => {
    setSize({ width: panelState.width, height: panelState.height });
  }, [panelState.width, panelState.height]);

  const handleInteraction = () => {
    if (onFocus) {
      onFocus(panelId);
    }
  };

  // 获取懒加载的组件
  const LazyPanelContent = getLazyComponent(contribution);

  return (
    // 1. Draggable 组件现在包裹一个简单的 Box，这个 Box 才是拖动的目标。
    <Draggable
      nodeRef={nodeRef}
      handle=".drag-handle"
      position={{ x: panelState.x, y: panelState.y }}
      onStart={handleInteraction}
      onStop={(e, data) => onDragStop(panelId, { x: data.x, y: data.y })}
      bounds="parent"
    >
      <Box
        ref={nodeRef}
        sx={{
          // 这个 Box 负责定位和层级
          position: 'absolute',
          top: 0,
          left: 0,
          width: size.width,
          height: size.height,
          zIndex: panelState.zIndex,
        }}
        // 点击容器任何地方都能触发 onFocus
        onMouseDown={handleInteraction}
      >
        {/* 使用 Suspense 包裹 ResizableBox */}
        <Suspense fallback={<LoadingPlaceholder />}>
          <ResizableBox
            width={size.width}
            height={size.height}
            onResize={(e, data) => setSize({ width: data.size.width, height: data.size.height })}
            onResizeStop={(e, data) => onResizeStop(panelId, { width: data.size.width, height: data.size.height })}
            minConstraints={[300, 200]}
            maxConstraints={[1200, 1000]}
            resizeHandles={['se']}
            handle={<CustomResizeHandle />}
            // ResizableBox 只需要填充其父容器即可
            style={{
              width: '100%',
              height: '100%',
            }}
          >
            {/* 渲染真正的懒加载组件 */}
            <LazyPanelContent services={services} />
          </ResizableBox>
        </Suspense>
      </Box>
    </Draggable>
  );
}