// plugins/core_goliath/src/dashboard/Dashboard.jsx

import * as React from 'react';

import { alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import AppNavbar from './components/AppNavbar';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import AppTheme from '../shared-theme/AppTheme';

// 1. 引入 useSandbox Hook 和我们的新视图
import { useSandbox } from '../context/SandboxContext';
import WelcomeView from '../views/WelcomeView';
import SandboxHomeView from '../views/SandboxHomeView';
import SandboxBuildView from '../views/SandboxBuildView';
import SandboxRunView from '../views/SandboxRunView';
import ImportSandboxDialog from './components/ImportSandboxDialog';

// 2. 创建一个辅助函数来选择要渲染的视图
const renderActiveView = (activeView, selectedSandbox) => {
    if (!selectedSandbox) {
        return <WelcomeView />;
    }

    switch (activeView) {
        case 'Home':
            return <SandboxHomeView />;
        case 'Build':
            return <SandboxBuildView />;
        case 'Run':
            return <SandboxRunView />;
        default:
            return <SandboxHomeView />; // 默认显示 Home
    }
};


export default function Dashboard(props) {
  // 3. 获取全局状态
  const { selectedSandbox, activeView } = useSandbox();
  
  return (
    <AppTheme {...props} >
         <ImportSandboxDialog /> 
      <Box sx={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column' }}>
        <CssBaseline enableColorScheme />
        <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
          <SideMenu />
          <AppNavbar />
          <Box
            component="main"
            sx={(theme) => ({
              flexGrow: 1,
              backgroundColor: theme.vars
                ? `rgba(${theme.vars.palette.background.defaultChannel} / 1)`
                : alpha(theme.palette.background.default, 1),
              overflow: 'auto',
            })}
          >
            <Stack
              spacing={2}
              sx={{
                alignItems: 'center',
                mx: 3,
                pb: 5,
                mt: { xs: 8, md: 0 },
              }}
            >
              <Header />
              {/* 4. 调用我们的渲染函数，替换掉原来的 <MainGrid /> */}
              {renderActiveView(activeView, selectedSandbox)}
            </Stack>
          </Box>
        </Box>
      </Box>
    </AppTheme>
  );
}