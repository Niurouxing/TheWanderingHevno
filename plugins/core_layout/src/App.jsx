// plugins/core_layout/src/main.jsx
import React from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { FloatingMenuButton } from './components/FloatingMenuButton';
import { PageContainer } from './components/PageContainer'; // 新组件
// --- 1. 导入新的对话框组件 ---
import { GlobalConfirmationDialog } from './components/GlobalConfirmationDialog';
// --- 2. 导入 useLayout Hook 以获取服务 ---
import { useLayout } from './context/LayoutContext';

const darkTheme = createTheme({ palette: { mode: 'dark' } });

// --- 3. 创建一个新的内部组件来访问 context ---
function AppContent() {
  const { services } = useLayout();
  const confirmationService = services.get('confirmationService');

  return (
    <>
      <CssBaseline />
      <Box sx={{ width: '100vw', height: '100vh', display: 'flex' }}>
        <Box component="main" sx={{ flexGrow: 1, position: 'relative' }}>
          <PageContainer />
          <FloatingMenuButton />
        </Box>
      </Box>
      {/* --- 4. 渲染全局对话框并传入服务实例 --- */}
      {confirmationService && <GlobalConfirmationDialog service={confirmationService} />}
    </>
  );
}

export function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      {/* LayoutProvider 必须在 AppContent 外面，这样 useLayout 才能工作 */}
      {/* 这里不再需要 ConfirmationProvider */}
      <AppContent /> 
    </ThemeProvider>
  );
}