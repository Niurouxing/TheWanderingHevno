// plugins/core_goliath/src/dashboard/components/SelectContent.jsx (带自定义图标显示)

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

// Avatar 和 ListItemAvatar 样式保持不变
const Avatar = styled(MuiAvatar)(({ theme }) => ({
  width: 28,
  height: 28,
  backgroundColor: (theme.vars || theme).palette.background.paper,
  color: (theme.vars || theme).palette.text.secondary,
  border: `1px solid ${(theme.vars || theme).palette.divider}`,
  // 1. 确保图片填充整个Avatar，而不是被裁剪
  '& .MuiAvatar-img': {
    objectFit: 'cover',
  },
}));

const ListItemAvatar = styled(MuiListItemAvatar)({
  minWidth: 0,
  marginRight: 12,
});

const DEFAULT_DISPLAY_ITEM = {
    name: 'Sitemark-web',
    icon_url: null, // 默认项没有icon_url
};

export default function SelectContent() {
  const { 
    sandboxes, 
    selectedSandbox, 
    loading, 
    fetchSandboxes, 
    selectSandbox,
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

  const currentSelectionId = selectedSandbox?.id || '';
  const currentDisplayItem = selectedSandbox || DEFAULT_DISPLAY_ITEM;

  return (
    <Select
      value={currentSelectionId}
      onChange={handleChange}
      disabled={loading}
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
      // 2. 修改 renderValue 以显示图标
      renderValue={() => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <ListItemAvatar sx={{ minWidth: 0 }}>
            {/* Avatar现在会尝试加载icon_url，如果失败则显示默认图标 */}
            <Avatar src={currentDisplayItem.icon_url}>
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
      
      {/* 3. 修改 MenuItem 列表以显示图标 */}
      {sandboxes.length > 0 
        ? (
            sandboxes.map((sandbox) => (
              <MenuItem key={sandbox.id} value={sandbox.id}>
                  <ListItemAvatar>
                    <Avatar src={sandbox.icon_url}>
                      {/* 如果 sandbox.icon_url 无效，则显示此默认图标 */}
                      <DevicesRoundedIcon sx={{ fontSize: '1rem' }} />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText primary={sandbox.name} secondary="Web app" />
              </MenuItem>
            ))
        ) 
        : (
            <MenuItem key="none-item" value="" disabled>
                <ListItemAvatar>
                  <Avatar> {/* 无 src，总是显示默认图标 */}
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
          <Avatar> {/* 无 src */}
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