// plugins/core_layout/src/components/FloatingMenu.jsx
import React, { useState, useRef, useMemo, useEffect } from 'react';
import Draggable from 'react-draggable';
import { useLayout } from '../context/LayoutContext';
import { Box, IconButton, Tooltip } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import * as MuiIcons from '@mui/icons-material';

const DynamicIcon = ({ name }) => {
  if (React.isValidElement(name)) {
    return name;
  }
  const Icon = MuiIcons[name];
  return Icon ? <Icon /> : <div/>;
};

// --- Constants for styling and layout ---
const COLLAPSED_SIZE = 40;
const ICON_SIZE = 35;
const GAP = 10;
const MAX_COLUMNS = 3;
// --- 定义拖动容差，单位为像素 ---
// 如果鼠标移动距离小于这个值，我们仍视其为一次点击
const DRAG_TOLERANCE = 5;

export function FloatingMenu() {
  const { pages, activePageId, setActivePageId, menuOverride } = useLayout();
  const draggableRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  
  // --- 使用一个 ref 来存储拖动的起始位置，而不是一个简单的布尔值 ---
  const dragInfo = useRef({ startX: 0, startY: 0 });

  useEffect(() => {
    if (isOpen) {
      draggableRef.current?.focus({ preventScroll: true });
    }
  }, [isOpen]);

  const actions = useMemo(() => {
    if (menuOverride) {
      return menuOverride;
    }
    return [
      { id: null, title: 'Home', icon: <HomeRoundedIcon />, onClick: () => setActivePageId(null) },
      ...pages
        .filter(page => page.menu) 
        .map(page => ({
          id: page.id,
          title: page.menu.title,
          icon: <DynamicIcon name={page.menu.icon} />,
          onClick: () => setActivePageId(page.id),
        }))
    ];
  }, [pages, menuOverride, setActivePageId]);

  const actualColumns = Math.min(actions.length, MAX_COLUMNS);
  const finalColumns = actualColumns > 0 ? actualColumns : 1;
  const rows = Math.ceil(actions.length / finalColumns);
  const EXPANDED_WIDTH = (ICON_SIZE * finalColumns) + (GAP * (finalColumns + 1));
  const EXPANDED_HEIGHT = (ICON_SIZE * rows) + (GAP * (rows + 1));

  const handleActionClick = (action) => {
    if (action.onClick) {
      action.onClick();
    }
    setIsOpen(false);
  };
  
  const handleBlur = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setIsOpen(false);
    }
  };

  // --- onStart: 记录鼠标按下的初始屏幕位置 ---
  const handleDragStart = (e) => {
    // 使用 clientX/Y，因为它们是相对于视口的，不受滚动影响
    dragInfo.current = {
        startX: e.clientX,
        startY: e.clientY,
    };
  };

  // --- onStop: 计算位移并决定这是否为一次点击 ---
  const handleDragStop = (e) => {
    const { startX, startY } = dragInfo.current;
    const endX = e.clientX;
    const endY = e.clientY;

    // 使用勾股定理计算移动的直线距离
    const distanceMoved = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));

    // 只有当移动距离小于容差值时，才认为这是一次点击
    if (distanceMoved < DRAG_TOLERANCE) {
      if (!isOpen) {
        setIsOpen(true);
      }
    }
    // 如果移动距离超过容差，我们什么都不做，这被视为一次合法的拖动。
  };

  const containerSx = {
    width: isOpen ? EXPANDED_WIDTH : COLLAPSED_SIZE,
    height: isOpen ? EXPANDED_HEIGHT : COLLAPSED_SIZE,
    backgroundColor: '#1C1F22',
    color: '#FFFFFF',
    borderRadius: isOpen ? '16px' : '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    boxShadow: '0 0 0 0.6px #000, 0 14px 50px -2px rgba(0,0,0,0.95)',
    cursor: isOpen ? 'default' : 'grab',
    overflow: 'hidden',
    transition: `all 0.45s cubic-bezier(0.4, 0, 0.2, 1)`,
    outline: 'none',
    '&:active': {
      cursor: isOpen ? 'default' : 'grabbing',
    }
  };

  return (
    <Draggable
      nodeRef={draggableRef}
      bounds="parent"
      disabled={isOpen}
      onStart={handleDragStart}
      onStop={handleDragStop}
    >
      <Box
        ref={draggableRef}
        sx={{ position: 'absolute', bottom: 40, left: 24, zIndex: 1300 }}
        tabIndex={-1}
        onBlur={handleBlur}
      >
        <Box sx={containerSx}>
          <MenuIcon sx={{
            fontSize: 22,
            opacity: isOpen ? 0 : 1,
            transition: 'opacity 0.2s linear',
          }}/>
          
          {actions.map((action, index) => {
            const row = Math.floor(index / finalColumns);
            const col = index % finalColumns;

            const targetTop = GAP + row * (ICON_SIZE + GAP);
            const targetLeft = GAP + col * (ICON_SIZE + GAP);

            return (
              <Box
                key={action.id || `action-${index}`}
                sx={{
                  position: 'absolute',
                  width: ICON_SIZE,
                  height: ICON_SIZE,
                  top: isOpen ? targetTop : '50%',
                  left: isOpen ? targetLeft : '50%',
                  transform: isOpen ? 'none' : 'translate(-50%, -50%)',
                  opacity: isOpen ? 1 : 0,
                  transition: `all 0.35s cubic-bezier(0.4, 0, 0.2, 1)`,
                  transitionDelay: isOpen ? `${index * 0.03}s` : '0s',
                  pointerEvents: isOpen ? 'all' : 'none',
                }}
              >
                <Tooltip title={action.title} placement="top">
                  <IconButton
                    onClick={() => handleActionClick(action)}
                    sx={{
                      width: '100%',
                      height: '100%',
                      color: '#FFFFFF',
                      backgroundColor: action.isActive ? 'rgba(231, 194, 150, 0.15)' : 'transparent',
                      transform: action.isActive ? 'scale(1.1)' : 'scale(1)',
                      transition: 'background-color 0.2s, transform 0.2s',
                      '&:hover': {
                        backgroundColor: '#474D50',
                        transform: 'scale(1.15)'
                      }
                    }}
                  >
                    {action.icon}
                  </IconButton>
                </Tooltip>
              </Box>
            );
          })}
        </Box>
      </Box>
    </Draggable>
  );
}