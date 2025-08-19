// plugins/core_layout/src/App.jsx
import React from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { PageContainer } from './components/PageContainer';
// --- 1. 导入新的 FloatingMenu 组件 ---
import { FloatingMenu } from './components/FloatingMenu';
import { GlobalConfirmationDialog } from './components/GlobalConfirmationDialog';
import { useLayout } from './context/LayoutContext';

const darkTheme = createTheme({ palette: { mode: 'dark' } });

function AppContent() {
  const { services } = useLayout();
  const confirmationService = services.get('confirmationService');

  return (
    <>
      <CssBaseline />
      <Box sx={{ width: '100vw', height: '100vh', display: 'flex' }}>
        <Box component="main" sx={{ flexGrow: 1, position: 'relative' }}>
          <PageContainer />
          {/* --- 2. 使用新的 FloatingMenu 组件 --- */}
          <FloatingMenu />
        </Box>
      </Box>
      {confirmationService && <GlobalConfirmationDialog service={confirmationService} />}
    </>
  );
}

export function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <AppContent /> 
    </ThemeProvider>
  );
}