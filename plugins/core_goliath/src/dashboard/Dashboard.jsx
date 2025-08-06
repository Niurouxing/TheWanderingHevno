// src/dashboard/Dashboard.jsx

import * as React from 'react';

import { alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import AppNavbar from './components/AppNavbar';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import AppTheme from '../shared-theme/AppTheme';


export default function Dashboard(props) {
  return (
    // AppTheme 是我们的 ThemeProvider
    <AppTheme {...props} >
      {/* 
        关键修复：
        在 AppTheme 之后，立即使用一个 Box 作为根容器。
        MUI 的 ThemeProvider 会将所有 CSS 变量（--template-palette...）
        作为内联样式或者在一个 <style> 块中定义，并应用到这个 Box 上。
        这样，这个 Box 内部的所有子组件就都能成功地访问到这些 CSS 变量了。
      */}
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
              {/* <MainGrid /> */}
            </Stack>
          </Box>
        </Box>
      </Box>
    </AppTheme>
  );
}