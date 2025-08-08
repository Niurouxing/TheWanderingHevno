// plugins/core_goliath/src/components/SelectContent.jsx 

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

import { useSandbox } from '../context/SandboxContext';

const Avatar = styled(MuiAvatar)(({ theme }) => ({
  width: 28,
  height: 28,
  backgroundColor: (theme.vars || theme).palette.background.paper,
  color: (theme.vars || theme).palette.text.secondary,
  border: `1px solid ${(theme.vars || theme).palette.divider}`,
  '& .MuiAvatar-img': {
    objectFit: 'cover',
  },
}));

const ListItemAvatar = styled(MuiListItemAvatar)({
  minWidth: 0,
  marginRight: 12,
});

const DEFAULT_DISPLAY_ITEM = {
    name: 'Select Sandbox',
    icon_url: null,
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
      inputProps={{ 'aria-label': 'Select Sandbox' }}
      fullWidth
      sx={{
        maxHeight: 56,
        width: 215,
        [`& .${selectClasses.select}`]: {
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          pl: 1,
        },
      }}
      renderValue={() => (
        <>
          <ListItemAvatar sx={{ minWidth: 0 }}>
            <Avatar src={currentDisplayItem.icon_url}>
              <DevicesRoundedIcon sx={{ fontSize: '1rem' }} />
            </Avatar>
          </ListItemAvatar>
          <ListItemText 
              primary={loading ? 'Loading...' : currentDisplayItem.name}
              secondary={currentSelectionId ? "Selected" : "No sandbox selected"}
              primaryTypographyProps={{ style: { textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}}
          />
        </>
      )}
    >
      <ListSubheader sx={{ pt: 0 }}>Your Sandboxes</ListSubheader>
      
      {sandboxes.length > 0 ? (
        sandboxes.map((sandbox) => (
          <MenuItem key={sandbox.id} value={sandbox.id}>
              <ListItemAvatar>
                <Avatar src={sandbox.icon_url}>
                  <DevicesRoundedIcon sx={{ fontSize: '1rem' }} />
                </Avatar>
              </ListItemAvatar>
              <ListItemText primary={sandbox.name} />
          </MenuItem>
        ))
      ) : (
        <MenuItem disabled>
            <ListItemText primary="No sandboxes found." sx={{ fontStyle: 'italic' }}/>
        </MenuItem>
      )}

      <Divider sx={{ mx: -1, my: 1 }} />

      <MenuItem value="create_new" onClick={handleCreateClick}>
        <ListItemIcon>
          <AddRoundedIcon />
        </ListItemIcon>
        <ListItemText primary="Import from PNG..." />
      </MenuItem>
    </Select>
  );
}