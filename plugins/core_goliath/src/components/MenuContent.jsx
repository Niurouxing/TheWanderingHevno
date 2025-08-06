// plugins/core_goliath/src/components/MenuContent.jsx

import * as React from 'react';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
// 1. 引入新的图标
import BuildRoundedIcon from '@mui/icons-material/BuildRounded';
import PlayCircleOutlineRoundedIcon from '@mui/icons-material/PlayCircleOutlineRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import InfoRoundedIcon from '@mui/icons-material/InfoRounded';
import HelpRoundedIcon from '@mui/icons-material/HelpRounded';

// 2. 引入 useSandbox Hook
import { useSandbox } from '../context/SandboxContext';

// 3. 定义新的主菜单项
const mainListItems = [
  { text: 'Home', icon: <HomeRoundedIcon />, view: 'Home' },
  { text: 'Build', icon: <BuildRoundedIcon />, view: 'Build' },
  { text: 'Run', icon: <PlayCircleOutlineRoundedIcon />, view: 'Run' },
];

// 次要菜单项保持不变，它们不依赖于沙盒选择
const secondaryListItems = [
  { text: 'Settings', icon: <SettingsRoundedIcon /> },
  { text: 'About', icon: <InfoRoundedIcon /> },
  { text: 'Feedback', icon: <HelpRoundedIcon /> },
];

export default function MenuContent() {
  // 4. 从 Context 获取所需的状态和方法
  const { selectedSandbox, activeView, setActiveView } = useSandbox();
  
  return (
    <Stack sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }}>
      <List dense>
        {mainListItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
            {/* 5. 添加控制逻辑 */}
            <ListItemButton
              // 如果没有选择沙盒，则禁用按钮
              disabled={!selectedSandbox}
              // 如果当前视图与此项匹配，则高亮显示
              selected={activeView === item.view}
              // 点击时，设置活动视图
              onClick={() => setActiveView(item.view)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      {/* 次要列表保持原样，没有任何特殊逻辑 */}
      <List dense>
        {secondaryListItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
            <ListItemButton>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Stack>
  );
}