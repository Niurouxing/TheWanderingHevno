// plugins/core_layout/src/components/FloatingMenuButton.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import Draggable from 'react-draggable';
import { useLayout } from '../context/LayoutContext';
import Box from '@mui/material/Box';
import SpeedDial from '@mui/material/SpeedDial';
import SpeedDialIcon from '@mui/material/SpeedDialIcon';
import SpeedDialAction from '@mui/material/SpeedDialAction';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import * as MuiIcons from '@mui/icons-material';

const DynamicIcon = ({ name }) => {
  const Icon = MuiIcons[name];
  return Icon ? <Icon /> : <div/>;
};

export function FloatingMenuButton() {
  const { pages, activePageId, setActivePageId } = useLayout();
  const draggableRef = useRef(null);

  const [direction, setDirection] = useState('up');
  const [tooltipPlacement, setTooltipPlacement] = useState('left');

  const updateDirections = useCallback(() => {
    if (!draggableRef.current) return;

    const rect = draggableRef.current.getBoundingClientRect();
    const viewHeight = window.innerHeight;
    const viewWidth = window.innerWidth;
    
    setDirection(rect.top > viewHeight / 2 ? 'up' : 'down');
    
    setTooltipPlacement(rect.left > viewWidth / 2 ? 'left' : 'right');
  }, []);

  useEffect(() => {
    updateDirections();
  }, [updateDirections]);


  const actions = [
    { 
      icon: <HomeRoundedIcon />, 
      name: 'Home',
      pageId: null,
    },
    ...pages
      .filter(page => page.menu) // 新增: 只添加有 menu 的页面到动作列表
      .map(page => ({
        icon: <DynamicIcon name={page.menu.icon} />,
        name: page.menu.title,
        pageId: page.id
      }))
  ];

  const handleActionClick = (pageId) => {
    setActivePageId(pageId);
  };
  
  const handleDragStop = () => {
    updateDirections();
  };

  return (
    <Draggable 
      nodeRef={draggableRef}
      handle=".MuiFab-primary"
      bounds="parent"
      onStop={handleDragStop}
    >
      <Box 
        ref={draggableRef} 
        sx={{ 
          position: 'absolute', 
          bottom: 24, 
          right: 24, 
          zIndex: 1300 
        }}
      >
        <SpeedDial
          ariaLabel="Main navigation"
          icon={<SpeedDialIcon />}
          direction={direction}
        >
          {actions.map((action) => (
            <SpeedDialAction
              key={action.name}
              icon={action.icon}
              tooltipTitle={action.name}
              tooltipPlacement={tooltipPlacement}
              onClick={() => handleActionClick(action.pageId)}
              sx={
                activePageId === action.pageId 
                ? {
                    '& .MuiFab-root': {
                      bgcolor: 'primary.main',
                      color: 'common.white',
                      '&:hover': {
                        bgcolor: 'primary.dark',
                      },
                    },
                  }
                : {} 
              }
            />
          ))}
        </SpeedDial>
      </Box>
    </Draggable>
  );
}