// plugins/core_goliath/src/dashboard/components/SelectContent.jsx

import React, { useEffect } from 'react';
import MuiAvatar from '@mui/material/Avatar';
import MuiListItemAvatar from '@mui/material/ListItemAvatar';
import MenuItem from '@mui/material/MenuItem';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListSubheader from '@mui/material/ListSubheader';
import Select, { selectClasses } from '@mui/material/Select';
import Divider from '@mui/material/Divider';
import { styled } from '@mui/material/styles';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import DevicesRoundedIcon from '@mui/icons-material/DevicesRounded';
import ConstructionRoundedIcon from '@mui/icons-material/ConstructionRounded';

import { useSandbox } from '../../context/SandboxContext';

const Avatar = styled(MuiAvatar)(({ theme }) => ({
  width: 28,
  height: 28,
  backgroundColor: (theme.vars || theme).palette.background.paper,
  color: (theme.vars || theme).palette.text.secondary,
  border: `1px solid ${(theme.vars || theme).palette.divider}`,
}));

const ListItemAvatar = styled(MuiListItemAvatar)({
  minWidth: 0,
  marginRight: 12,
});

// 1. 定义默认显示对象，但其ID现在是空字符串 ''
const DEFAULT_DISPLAY_ITEM = {
    name: 'Sitemark-web',
};

export default function SelectContent() {
  const { 
    sandboxes, 
    selectedSandbox, 
    loading, 
    fetchSandboxes, 
    selectSandbox,
    createSandbox
  } = useSandbox();

  useEffect(() => {
    fetchSandboxes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (event) => {
    const sandboxId = event.target.value;
    
    if (sandboxId === 'create_new') {
        return;
    }

    const newSelectedSandbox = sandboxes.find(s => s.id === sandboxId) || null;
    selectSandbox(newSelectedSandbox);
  };
  
  const handleCreateClick = () => {
    console.log('[SelectContent] "Add product" clicked, triggering import dialog...');
    const hookManager = window.Hevno.services.get('hookManager');
    if (hookManager) {
        hookManager.trigger('ui.show.importSandboxDialog');
    } else {
        console.error('[SelectContent] hookManager service not found!');
    }
  };

  // 2. 当前选择ID现在是真实ID或空字符串 ''
  const currentSelectionId = selectedSandbox?.id || '';
  const currentDisplayItem = selectedSandbox || DEFAULT_DISPLAY_ITEM;

  return (
    <Select
      value={currentSelectionId}
      onChange={handleChange}
      disabled={loading}
      // 关键：确保Select组件知道如何处理空值''
      displayEmpty 
      inputProps={{ 'aria-label': 'Select company' }}
      fullWidth
      sx={{
        maxHeight: 56,
        width: 215,
        [`& .${selectClasses.select}`]: {
          display: 'flex',
          alignItems: 'center',
          gap: '2px',
          pl: 1,
        },
      }}
      renderValue={() => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ListItemAvatar sx={{ minWidth: 0 }}>
            <Avatar alt={currentDisplayItem.name}>
                <DevicesRoundedIcon sx={{ fontSize: '1rem' }} />
            </Avatar>
          </ListItemAvatar>
          <ListItemText 
              primary={loading ? 'Loading...' : currentDisplayItem.name}
              secondary="Web app"
              primaryTypographyProps={{ style: { textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}}
          />
        </div>
      )}
    >
      <ListSubheader sx={{ pt: 0 }}>Production</ListSubheader>
      
      {/* 3. 调整渲染逻辑 */}
      {sandboxes.length > 0 
        ? (
            // 如果有沙盒，则渲染沙盒列表
            sandboxes.map((sandbox) => (
              <MenuItem key={sandbox.id} value={sandbox.id}>
                  <ListItemAvatar>
                    <Avatar alt={sandbox.name}>
                      <DevicesRoundedIcon sx={{ fontSize: '1rem' }} />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText primary={sandbox.name} secondary="Web app" />
              </MenuItem>
            ))
        ) 
        : (
            // 如果没有沙盒（或正在加载），渲染一个禁用的默认项来占位
            <MenuItem key="none-item" value="" disabled>
                <ListItemAvatar>
                  <Avatar alt={DEFAULT_DISPLAY_ITEM.name}>
                    <DevicesRoundedIcon sx={{ fontSize: '1rem' }} />
                  </Avatar>
                </ListItemAvatar>
                <ListItemText primary={DEFAULT_DISPLAY_ITEM.name} secondary="Web app" />
            </MenuItem>
        )
      }

      <ListSubheader>Development</ListSubheader>
      <MenuItem value="dev_placeholder" disabled>
        <ListItemAvatar>
          <Avatar alt="Sitemark Admin">
            <ConstructionRoundedIcon sx={{ fontSize: '1rem' }} />
          </Avatar>
        </ListItemAvatar>
        <ListItemText primary="Sitemark-Admin" secondary="Web app" />
      </MenuItem>
      
      <Divider sx={{ mx: -1 }} />

      <MenuItem value="create_new" onClick={handleCreateClick}>
        <ListItemIcon>
          <AddRoundedIcon />
        </ListItemIcon>
        <ListItemText primary="Add product" />
      </MenuItem>
    </Select>
  );
}