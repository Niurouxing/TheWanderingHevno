// plugins/core_runner_ui/src/components/FloatingPanel.jsx
import React, { useState, useEffect, useRef } from 'react';
import Draggable from 'react-draggable';
import { ResizableBox } from 'react-resizable';
import { Box } from '@mui/material';

import 'react-resizable/css/styles.css';

const CustomResizeHandle = React.forwardRef((props, ref) => {
  const { handleAxis, ...restProps } = props;
  return (
    <Box
      ref={ref}
      {...restProps}
      sx={{
        position: 'absolute',
        width: 20,
        height: 20,
        bottom: 0,
        right: 0,
        cursor: 'se-resize',
        '&::after': {
          content: '""',
          position: 'absolute',
          right: '4px',
          bottom: '4px',
          width: '6px',
          height: '6px',
          borderRight: '2px solid rgba(255, 255, 255, 0.5)',
          borderBottom: '2px solid rgba(255, 255, 255, 0.5)',
          transition: 'all 0.2s ease',
        },
        '&:hover::after': {
          borderRightColor: 'rgba(255, 255, 255, 0.8)',
          borderBottomColor: 'rgba(255, 255, 255, 0.8)',
        }
      }}
    />
  );
});

export function FloatingPanel({
  panelId,
  panelState,
  onDragStop,
  onResizeStop,
  onFocus,
  children
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
        {/* 
          2. ResizableBox 现在位于 Draggable 的稳定子节点内部。
             它不再需要 ref，也不需要绝对定位，因为它会填满父级的 Box。
        */}
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
          {/* 
            3. 子组件(例如 MomentInspectorPanel) 的样式 `height: '100%'`
               现在会使其填满 ResizableBox，一切正常。
          */}
          {children}
        </ResizableBox>
      </Box>
    </Draggable>
  );
}