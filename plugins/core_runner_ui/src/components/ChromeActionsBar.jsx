// plugins/core_runner_ui/src/components/ChromeActionsBar.jsx
import React from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import * as MuiIcons from '@mui/icons-material';

// 一个可复用的动态图标加载器
const DynamicIcon = ({ name }) => {
  if (React.isValidElement(name)) return name;
  const Icon = MuiIcons[name];
  return Icon ? <Icon fontSize="small" /> : null;
};

/**
 * 渲染在驾驶舱右上角的全局操作按钮。
 * 这些按钮通常用于切换浮动面板的可见性。
 */
export function ChromeActionsBar({ actions, activePanelIds, onTogglePanel }) {
  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 16,
        right: 16,
        zIndex: 1100, // 高于面板(2)，低于管理弹窗(10)和浮动菜单(1300)
        display: 'flex',
        gap: 1.5, // 按钮之间的间距
      }}
    >
      {actions.map(action => {
        const isActive = activePanelIds.includes(action.panelId);
        return (
          <Tooltip title={action.title} placement="bottom" key={action.id}>
            <IconButton
              onClick={() => onTogglePanel(action.panelId)}
              sx={{
                color: isActive ? 'primary.main' : '#FFFFFF',
                backgroundColor: 'rgba(44, 44, 46, 0.25)',
                backdropFilter: 'blur(5px) saturate(200%)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: '0 4px 12px 0 rgba(0, 0, 0, 0.15)',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  backgroundColor: 'rgba(70, 70, 70, 0.4)',
                  transform: 'scale(1.1)',
                },
              }}
            >
              <DynamicIcon name={action.icon} />
            </IconButton>
          </Tooltip>
        );
      })}
    </Box>
  );
}
