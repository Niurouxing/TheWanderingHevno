// plugins/core_layout/src/components/FloatingMenuButton.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react'; // 1. 导入新钩子
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

  // 2. 添加新的状态来控制方向
  const [direction, setDirection] = useState('up');
  const [tooltipPlacement, setTooltipPlacement] = useState('left');

  // 3. 创建位置检测函数，并用 useCallback 优化
  const updateDirections = useCallback(() => {
    if (!draggableRef.current) return;

    const rect = draggableRef.current.getBoundingClientRect();
    const viewHeight = window.innerHeight;
    const viewWidth = window.innerWidth;
    
    // 检查垂直位置
    // 如果按钮的上边缘在屏幕下半部分，则向上展开，反之向下
    setDirection(rect.top > viewHeight / 2 ? 'up' : 'down');
    
    // 检查水平位置
    // 如果按钮的左边缘在屏幕右半部分，则标签在左侧，反之在右侧
    setTooltipPlacement(rect.left > viewWidth / 2 ? 'left' : 'right');
  }, []); // 空依赖数组，函数只创建一次

  // 4. 在组件首次加载时运行方向检测
  useEffect(() => {
    updateDirections();
  }, [updateDirections]);


  const actions = [
    { 
      icon: <HomeRoundedIcon />, 
      name: 'Home',
      pageId: null,
    },
    ...pages.map(page => ({
      icon: <DynamicIcon name={page.menu.icon} />,
      name: page.menu.title,
      pageId: page.id
    }))
  ];

  const handleActionClick = (pageId) => {
    setActivePageId(pageId);
  };
  
  // 5. 定义拖拽结束时的回调函数
  const handleDragStop = () => {
    // 拖拽结束后，重新计算方向
    updateDirections();
  };

  return (
    <Draggable 
      nodeRef={draggableRef}
      handle=".MuiFab-primary"
      bounds="parent"
      onStop={handleDragStop} // 6. 挂载拖拽结束回调
    >
      <Box 
        ref={draggableRef} 
        sx={{ 
          position: 'absolute', 
          // 初始位置，可以保持不变或调整
          bottom: 24, 
          right: 24, 
          zIndex: 1300 
        }}
      >
        <SpeedDial
          ariaLabel="Main navigation"
          icon={<SpeedDialIcon />}
          direction={direction} // 7. 应用动态方向
        >
          {actions.map((action) => (
            <SpeedDialAction
              key={action.name}
              icon={action.icon}
              tooltipTitle={action.name}
              tooltipPlacement={tooltipPlacement} // 8. 应用动态标签位置
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