// plugins/core_layout/src/components/FloatingMenuButton.jsx
import React, { useState } from 'react';
import { useLayout } from '../context/LayoutContext';
import Fab from '@mui/material/Fab';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
// 动态加载MUI图标
import * as MuiIcons from '@mui/icons-material';

const DynamicIcon = ({ name }) => {
  const Icon = MuiIcons[name];
  return Icon ? <Icon /> : <div/>;
};

export function FloatingMenuButton() {
  const { pages, activePageId, setActivePageId } = useLayout();
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleClick = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  const handleMenuItemClick = (pageId) => {
    setActivePageId(pageId);
    handleClose();
  };

  return (
    <>
      <Fab
        color="primary"
        aria-label="main menu"
        onClick={handleClick}
        sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1300 }}
      >
        <MenuRoundedIcon />
      </Fab>
      <Menu anchorEl={anchorEl} open={open} onClose={handleClose}>
        <MenuItem onClick={() => handleMenuItemClick(null)} selected={activePageId === null}>
          <ListItemIcon><HomeRoundedIcon fontSize="small" /></ListItemIcon>
          <ListItemText>Home</ListItemText>
        </MenuItem>
        {pages.map((page) => (
          <MenuItem
            key={page.id}
            onClick={() => handleMenuItemClick(page.id)}
            selected={page.id === activePageId}
          >
            <ListItemIcon><DynamicIcon name={page.menu.icon} /></ListItemIcon>
            <ListItemText>{page.menu.title}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}