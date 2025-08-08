// plugins/core_layout/src/main.jsx
import React from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { FloatingMenuButton } from './components/FloatingMenuButton';
import { PageContainer } from './components/PageContainer'; // 新组件

const darkTheme = createTheme({ palette: { mode: 'dark' } });

export function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box sx={{ width: '100vw', height: '100vh', display: 'flex' }}>
        <Box component="main" sx={{ flexGrow: 1, position: 'relative' }}>
          {/* 渲染活动页面的容器 */}
          <PageContainer />
          {/* 浮动按钮现在渲染在主内容区之上 */}
          <FloatingMenuButton />
        </Box>
      </Box>
    </ThemeProvider>
  );
}