// plugins/core_runner_ui/src/components/FloatingPanel.jsx
import React from 'react';
import Draggable from 'react-draggable';
import { Box } from '@mui/material';

export function FloatingPanel({
  panelId,
  panelState, // { x, y, width, height, zIndex }
  onDragStop,
  onFocus,
  children
}) {
  const nodeRef = React.useRef(null);

  const handleInteraction = () => {
    if (onFocus) {
      onFocus(panelId);
    }
  };

  return (
    <Draggable
      nodeRef={nodeRef}
      handle=".drag-handle" // 各个面板内部定义的拖动手柄
      position={{ x: panelState.x, y: panelState.y }}
      onStart={handleInteraction}
      onStop={(e, data) => onDragStop(panelId, { x: data.x, y: data.y })}
      bounds="parent"
    >
      <Box
        ref={nodeRef}
        onMouseDown={handleInteraction}
        sx={{
          // 核心变化：这是一个透明的定位容器，不带任何UI样式
          position: 'absolute',
          top: 0, // Draggable 通过 transform 来定位，这里设为0
          left: 0,
          width: panelState.width,
          height: panelState.height,
          zIndex: panelState.zIndex,
          
          // 注意：这里的 resize 和 overflow 是为容器本身服务的，
          // 不会影响子组件的内部样式。
          // resize: 'both',  // 如果你希望保留浏览器原生缩放，可以取消注释
          // overflow: 'hidden', // 防止内容溢出
        }}
      >
        {/* 
          children (即 MomentInspectorPanel 或 SnapshotHistoryPanel) 
          现在可以完全控制自己的样式。
          由于它们内部的 Paper 组件设置了 height: '100%' 和 width: '100%',
          它们会完美地填充这个透明容器。
        */}
        {children}
      </Box>
    </Draggable>
  );
}