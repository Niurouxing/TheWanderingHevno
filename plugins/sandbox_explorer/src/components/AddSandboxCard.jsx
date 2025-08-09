// plugins/sandbox_explorer/src/components/AddSandboxCard.jsx

import React from 'react';
import { Card, CardActionArea, Box, Typography } from '@mui/material';
import AddCircleOutlineRoundedIcon from '@mui/icons-material/AddCircleOutlineRounded';

export function AddSandboxCard({ onClick }) {
  return (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex',
        // 使用虚线边框来与实体卡片区分
        border: (theme) => `2px dashed ${theme.palette.divider}`,
        // 移除阴影，让它看起来更像一个占位符
        boxShadow: 'none',
      }}
    >
      <CardActionArea
        onClick={onClick}
        sx={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          p: 2,
          transition: 'background-color 0.2s',
          '&:hover': {
            backgroundColor: (theme) => theme.palette.action.hover,
          }
        }}
      >
        <AddCircleOutlineRoundedIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
        <Typography variant="h6" color="text.secondary" sx={{ mt: 1 }}>
          Import New Sandbox
        </Typography>
      </CardActionArea>
    </Card>
  );
}